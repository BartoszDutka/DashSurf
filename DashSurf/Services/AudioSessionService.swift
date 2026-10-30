import AVFoundation

actor AudioSessionService {
    static let shared = AudioSessionService()

    func activatePlaybackCategory() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .moviePlayback, options: [.allowAirPlay, .allowBluetoothA2DP])
            try session.setActive(true)
        } catch {
            // Ignore — sites can still play with system defaults.
        }
    }
}
