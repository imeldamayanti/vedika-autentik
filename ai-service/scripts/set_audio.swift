// Set the macOS default output and input devices by name.
//   swift scripts/set_audio.swift "BlackHole 2ch" "BlackHole 16ch"
//   swift scripts/set_audio.swift "MacBook Pro Speakers" "MacBook Pro Microphone"
import CoreAudio
func devices() -> [(AudioDeviceID, String)] {
    var addr = AudioObjectPropertyAddress(mSelector: kAudioHardwarePropertyDevices, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    var size = UInt32(0)
    AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size)
    var ids = [AudioDeviceID](repeating: 0, count: Int(size) / MemoryLayout<AudioDeviceID>.size)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &ids)
    return ids.map { id in
        var cf: CFString = "" as CFString; var n = UInt32(MemoryLayout<CFString>.size)
        var a = AudioObjectPropertyAddress(mSelector: kAudioObjectPropertyName, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
        AudioObjectGetPropertyData(id, &a, 0, nil, &n, &cf)
        return (id, cf as String)
    }
}
func setDefault(_ selector: AudioObjectPropertySelector, _ name: String) {
    guard var id = devices().first(where: { $0.1 == name })?.0 else { print("not found:", name); return }
    var addr = AudioObjectPropertyAddress(mSelector: selector, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    let status = AudioObjectSetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, UInt32(MemoryLayout<AudioDeviceID>.size), &id)
    print(selector == kAudioHardwarePropertyDefaultOutputDevice ? "output ->" : "input  ->", name, status == 0 ? "ok" : "failed \(status)")
}
let args = CommandLine.arguments
setDefault(kAudioHardwarePropertyDefaultOutputDevice, args[1])
setDefault(kAudioHardwarePropertyDefaultInputDevice, args[2])
