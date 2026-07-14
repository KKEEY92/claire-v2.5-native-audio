import SwiftUI
import WebKit

@main
struct ClairemacOSApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        MenuBarExtra("Claire", systemImage: "waveform.circle.fill") {
            ContentView()
                .frame(width: 380, height: 600)
        }
        .menuBarExtraStyle(.window)
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var process: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        startBackend()
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopBackend()
    }

    func startBackend() {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        
        let workspacePath = "/Users/kevinkuck/01_VIBE_Code_AGENTIC_AI_KEV/00_PROJECTE_MAIN/01_Active_Workspace/claire-v2.5-native-audio"
        process.arguments = [
            "bash", "-c", "cd '\(workspacePath)/backend' && ../.venv/bin/python launcher.py"
        ]
        
        process.standardOutput = Pipe()
        process.standardError = Pipe()
        
        do {
            try process.run()
            self.process = process
            print("Python-Backend im Hintergrund gestartet (PID: \(process.processIdentifier))")
        } catch {
            print("Fehler beim Starten des Python-Backends: \(error)")
        }
    }

    func stopBackend() {
        if let process = process, process.isRunning {
            process.terminate()
            print("Python-Backend beendet")
        }
    }
}
