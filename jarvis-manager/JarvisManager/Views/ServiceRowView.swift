import SwiftUI

struct ServiceRowView: View {
    let service: Service

    var body: some View {
        HStack(spacing: 12) {
            // Status-Dot
            Circle()
                .fill(dotColor)
                .frame(width: 8, height: 8)
                .shadow(color: dotColor.opacity(0.8), radius: 4)

            // Name
            Text(service.displayName)
                .font(.custom("Courier New", size: 13))
                .foregroundColor(HUDColor.text)
                .frame(width: 120, alignment: .leading)

            // Port
            if let port = service.port {
                Text(":\(port)")
                    .font(.custom("Courier New", size: 12))
                    .foregroundColor(HUDColor.blue)
                    .frame(width: 50, alignment: .leading)
            } else {
                Text("")
                    .frame(width: 50)
            }

            Spacer()

            // Status-Label
            Text(service.status.label)
                .font(.custom("Courier New", size: 11))
                .fontWeight(.bold)
                .foregroundColor(dotColor)
                .tracking(1)
        }
        .padding(.vertical, 5)
        .padding(.horizontal, 12)
        .background(
            RoundedRectangle(cornerRadius: 2)
                .fill(HUDColor.panelBg.opacity(0.4))
        )
    }

    private var dotColor: Color {
        switch service.status {
        case .running:           return HUDColor.green
        case .stopped:           return HUDColor.red
        case .zombie:            return HUDColor.orange
        case .starting, .stopping: return HUDColor.blue
        case .unknown:           return HUDColor.gray
        }
    }
}
