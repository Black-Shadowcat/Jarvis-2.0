import Foundation

struct ShellResult {
    let output: String
    let error: String
    let exitCode: Int32
}

// Thin wrapper around Process() for running shell commands.
// All methods are async and non-blocking.
enum ShellExecutor {

    static func run(_ executable: String, args: [String]) async -> ShellResult {
        await withCheckedContinuation { continuation in
            DispatchQueue.global().async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: executable)
                process.arguments = args

                let outPipe = Pipe()
                let errPipe = Pipe()
                process.standardOutput = outPipe
                process.standardError = errPipe

                do {
                    try process.run()
                    process.waitUntilExit()
                } catch {
                    continuation.resume(returning: ShellResult(output: "", error: error.localizedDescription, exitCode: -1))
                    return
                }

                let out = String(data: outPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                let err = String(data: errPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                continuation.resume(returning: ShellResult(output: out, error: err, exitCode: process.terminationStatus))
            }
        }
    }

    // Fuer Scripts die laenger laufen: live output via callback streamen
    static func runStreaming(
        script: String,
        onLine: @escaping @Sendable (String) -> Void,
        onDone: @escaping @Sendable (Int32) -> Void
    ) {
        DispatchQueue.global().async {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/bin/bash")
            process.arguments = [script]

            let pipe = Pipe()
            process.standardOutput = pipe
            process.standardError = pipe

            // Live-Zeilen an Callback liefern
            pipe.fileHandleForReading.readabilityHandler = { handle in
                let data = handle.availableData
                guard !data.isEmpty,
                      let text = String(data: data, encoding: .utf8) else { return }
                for line in text.components(separatedBy: "\n") where !line.isEmpty {
                    onLine(line)
                }
            }

            do {
                try process.run()
            } catch {
                onLine("Fehler: \(error.localizedDescription)")
                onDone(-1)
                return
            }

            process.waitUntilExit()
            pipe.fileHandleForReading.readabilityHandler = nil
            onDone(process.terminationStatus)
        }
    }
}
