import CoreLocation
import Foundation

/// Conservative motion gate for car-screen video. There is no public CarPlay API
/// that reports "vehicle is parked". Speed from Core Location is a best-effort proxy.
/// If location is denied, we do NOT block playback (cannot measure ≠ driving).
final class CarMotionGate: NSObject, CLLocationManagerDelegate {
    static let shared = CarMotionGate()
    static let stateChanged = Notification.Name("DashSurf.CarMotionGateChanged")

    private(set) var isMoving = false
    private let manager = CLLocationManager()
    private var running = false
    private let movingSpeed: CLLocationSpeed = 3.0
    private let samplesToFlip = 3
    private var agreeing = 0

    private override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyKilometer
        manager.distanceFilter = 10
        manager.pausesLocationUpdatesAutomatically = true
    }

    func start() {
        guard !running else { return }
        running = true
        if manager.authorizationStatus == .notDetermined {
            manager.requestWhenInUseAuthorization()
        }
        manager.startUpdatingLocation()
    }

    func stop() {
        guard running else { return }
        running = false
        manager.stopUpdatingLocation()
        setMoving(false)
    }

    private func setMoving(_ moving: Bool) {
        guard moving != isMoving else { return }
        isMoving = moving
        NotificationCenter.default.post(name: CarMotionGate.stateChanged, object: nil)
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let speed = locations.last?.speed, speed >= 0 else { return }
        let moving = speed > movingSpeed
        if moving == isMoving {
            agreeing = 0
            return
        }
        agreeing += 1
        if agreeing >= samplesToFlip {
            agreeing = 0
            setMoving(moving)
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // No fix is not evidence of driving.
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        if manager.authorizationStatus == .denied || manager.authorizationStatus == .restricted {
            setMoving(false)
        }
    }
}
