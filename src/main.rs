#![allow(unused)]
#![windows_subsystem = "windows"]

use std::process::Command;
use serde::{Deserialize, Serialize};
use serde_json::{Result, Value};
use std::env;
use std::env::current_dir;
use std::fs;
use tao::{
    event::Event,
    event_loop::{ControlFlow, EventLoopBuilder},
};
use tray_icon::{
    menu::{AboutMetadata, Menu, MenuEvent, MenuItem, PredefinedMenuItem},
    TrayIconBuilder, TrayIconEvent,
};
use std::thread;
use std::time::Duration;

#[derive(Serialize, Deserialize)]
struct Settings {
    input_folder: String,
    output_folder: String,
}

enum UserEvent {
    TrayIconEvent(tray_icon::TrayIconEvent),
    MenuEvent(tray_icon::menu::MenuEvent),
    RunPython,
}

fn load_icon(path: &std::path::Path) -> tray_icon::Icon {
    let (icon_rgba, icon_width, icon_height) = {
        let image = image::open(path)
            .expect("Failed to open icon path")
            .into_rgba8();
        let (width, height) = image.dimensions();
        let rgba = image.into_raw();
        (rgba, width, height)
    };
    tray_icon::Icon::from_rgba(icon_rgba, icon_width, icon_height).expect("Failed to open icon")
}

fn run_python() {
    let python = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };

    let program_status = Command::new(python)
        .arg("src/main.py")
        .status();

    match program_status {
        Ok(status) if status.success() => {
            println!("PACS send script ran successfully");
        }
        Ok(status) => {
            eprintln!("Script exited with code {}", status);
        }
        Err(e) => {
            eprintln!("Failed to run Python script: {}", e);
        }
    }
}

fn main() {
    // Loads the tray icon
    let current_directory = env::current_dir().expect("error finding current directory");
    println!("curr {}", current_directory.clone().display());
    let mut icon_path = current_directory.clone();
    icon_path.push("assets");
    icon_path.push("icon.png");
    println!("icon {}", icon_path.clone().display());

    let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build();

    // set a tray event handler that forwards the event and wakes up the event loop
    let proxy = event_loop.create_proxy();
    TrayIconEvent::set_event_handler(Some(move |event| {
        proxy.send_event(UserEvent::TrayIconEvent(event));
    }));

    let proxy = event_loop.create_proxy();
    thread::spawn(move || {
        loop {
            thread::sleep(Duration::from_secs(3600)); // Run every hour

            if proxy.send_event(UserEvent::RunPython).is_err() {
                // Event loop has exited
                break;
            }
        }
    });

    // set a menu event handler that forwards the event and wakes up the event loop
    let proxy = event_loop.create_proxy();
    MenuEvent::set_event_handler(Some(move |event| {
        proxy.send_event(UserEvent::MenuEvent(event));
    }));

    // Make the tray menu 
    let tray_menu = Menu::new();
    let quit_entry = MenuItem::new("Quit", true, None);
    let run_pacs_send_entry = MenuItem::new("Run PACS send", true, None);
    tray_menu.append_items(&[
        &run_pacs_send_entry,
        &quit_entry,
    ]);

    let mut tray_icon = None;

    let menu_channel = MenuEvent::receiver();
    let tray_channel = TrayIconEvent::receiver();

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;

        match event {
            Event::NewEvents(tao::event::StartCause::Init) => {
                let icon = load_icon(std::path::Path::new(icon_path.to_str().unwrap()));

                // We create the icon once the event loop is actually running
                // to prevent issues like https://github.com/tauri-apps/tray-icon/issues/90
                tray_icon = Some(
                    TrayIconBuilder::new()
                        .with_menu(Box::new(tray_menu.clone()))
                        .with_tooltip("tao - awesome windowing lib")
                        .with_icon(icon)
                        .build()
                        .unwrap(),
                );

                // We have to request a redraw here to have the icon actually show up.
                // Tao only exposes a redraw method on the Window so we use core-foundation directly.
                #[cfg(target_os = "macos")]
                unsafe {
                    use core_foundation::runloop::{CFRunLoopGetMain, CFRunLoopWakeUp};

                    let rl = CFRunLoopGetMain();
                    CFRunLoopWakeUp(rl);
                }
            }

            Event::UserEvent(UserEvent::TrayIconEvent(event)) => {
                println!("{event:?}");
            }
            Event::UserEvent(UserEvent::RunPython) => {
                run_python();
            }

            Event::UserEvent(UserEvent::MenuEvent(event)) => {
                println!("{event:?}");

                if event.id == quit_entry.id() {
                    tray_icon.take();
                    *control_flow = ControlFlow::Exit;
                } else if event.id == run_pacs_send_entry.id() {
                    println!("runnn pacs send");
                    run_python();
                }
            }

            _ => {}
        }
    })
}
