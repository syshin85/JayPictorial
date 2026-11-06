// Puts a cut-out picture (e.g. a spacecraft render on a white or transparent background) on a
// black 4:3 sky and saves it as JPEG, so it looks like the other space photos.
// The background is found by flood-filling near-white / transparent pixels from the edges,
// so white parts inside the spacecraft stay. Used by fetch_media.py for .png files.
// Usage: swift tools/on_black.swift in.png out.jpg width
import AppKit

let args = CommandLine.arguments
guard args.count == 4, let src = NSImage(contentsOfFile: args[1]), let width = Int(args[3]) else {
    FileHandle.standardError.write("usage: on_black.swift in.png out.jpg width\n".data(using: .utf8)!)
    exit(1)
}
var rect = CGRect(origin: .zero, size: src.size)
let cg = src.cgImage(forProposedRect: &rect, context: nil, hints: nil)!
let pw = cg.width, ph = cg.height

// 1. the picture as RGBA pixels, on black
let rgb = CGColorSpaceCreateDeviceRGB()
let pic = CGContext(data: nil, width: pw, height: ph, bitsPerComponent: 8, bytesPerRow: pw * 4,
                    space: rgb, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
pic.draw(cg, in: CGRect(x: 0, y: 0, width: pw, height: ph))
let px = pic.data!.bindMemory(to: UInt8.self, capacity: pw * ph * 4)

// 2. flood-fill the background from the edges and paint it black
func isBackground(_ i: Int) -> Bool {
    let a = Int(px[i * 4 + 3])
    if a < 16 { return true }
    return px[i * 4] > 232 && px[i * 4 + 1] > 232 && px[i * 4 + 2] > 232
}
var seen = [Bool](repeating: false, count: pw * ph)
var stack: [Int] = []
for x in 0..<pw { stack.append(x); stack.append((ph - 1) * pw + x) }
for y in 0..<ph { stack.append(y * pw); stack.append(y * pw + pw - 1) }
while let i = stack.popLast() {
    if seen[i] || !isBackground(i) { continue }
    seen[i] = true
    px[i * 4] = 0; px[i * 4 + 1] = 0; px[i * 4 + 2] = 0; px[i * 4 + 3] = 255
    let x = i % pw, y = i / pw
    if x > 0 { stack.append(i - 1) }
    if x < pw - 1 { stack.append(i + 1) }
    if y > 0 { stack.append(i - pw) }
    if y < ph - 1 { stack.append(i + pw) }
}
let cut = pic.makeImage()!

// 3. centre it on a black 4:3 canvas
let w = width, h = width * 3 / 4
let scale = min(CGFloat(w) * 0.9 / CGFloat(pw), CGFloat(h) * 0.9 / CGFloat(ph))
let dw = CGFloat(pw) * scale, dh = CGFloat(ph) * scale
let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                    space: rgb, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
ctx.setFillColor(CGColor(red: 0, green: 0, blue: 0, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
ctx.interpolationQuality = .high
ctx.draw(cut, in: CGRect(x: (CGFloat(w) - dw) / 2, y: (CGFloat(h) - dh) / 2, width: dw, height: dh))

let out = NSBitmapImageRep(cgImage: ctx.makeImage()!)
try! out.representation(using: .jpeg, properties: [.compressionFactor: 0.88])!.write(to: URL(fileURLWithPath: args[2]))
