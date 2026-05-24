import SwiftUI

struct LogView: View {
    let entries: [LogEntry]

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(entries) { entry in
                        LogRowView(entry: entry)
                            .id(entry.id)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            }
            .onChange(of: entries.count) { _ in
                if let last = entries.last {
                    withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                }
            }
        }
    }
}

private struct LogRowView: View {
    let entry: LogEntry

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text(entry.timeString)
                .font(.custom("Courier New", size: 11))
                .foregroundColor(HUDColor.blue)
                .frame(width: 70, alignment: .leading)

            Text(entry.level.prefix)
                .font(.custom("Courier New", size: 11))
                .fontWeight(.bold)
                .foregroundColor(levelColor)
                .frame(width: 30, alignment: .leading)

            Text(entry.message)
                .font(.custom("Courier New", size: 11))
                .foregroundColor(HUDColor.textDim)
                .lineLimit(nil)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.vertical, 3)
        .padding(.horizontal, 4)
    }

    private var levelColor: Color {
        switch entry.level {
        case .ok:    return HUDColor.green
        case .warn:  return HUDColor.orange
        case .error: return HUDColor.red
        case .info:  return HUDColor.blue
        }
    }
}
