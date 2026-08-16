// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CEOOSMacHelper",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "ceo-os-mac-helper", targets: ["CEOOSMacHelper"])],
    targets: [.executableTarget(name: "CEOOSMacHelper")]
)
