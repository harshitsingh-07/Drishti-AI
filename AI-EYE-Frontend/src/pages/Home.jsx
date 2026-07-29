import { useEffect, useRef, useState } from 'react'
import { MapPin } from 'lucide-react'
import Footer from '../components/Footer.jsx'
import Header from '../components/Header.jsx'
import { detectObjects } from '../services/authService.js'
import styles from './Home.module.css'

function Home() {
  const videoRef = useRef(null)
  const [isDetecting, setIsDetecting] = useState(false)
  const [isSharingLocation, setIsSharingLocation] = useState(false)
  const [status, setStatus] = useState('Ready. Double tap start to begin.')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let stream
    let intervalId

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
      } catch (err) {
        setError('Camera access was denied or unavailable.')
      }
    }

    if (isDetecting) {
      startCamera()
      intervalId = window.setInterval(async () => {
        if (!videoRef.current) return
        const canvas = document.createElement('canvas')
        canvas.width = videoRef.current.videoWidth || 320
        canvas.height = videoRef.current.videoHeight || 240
        const context = canvas.getContext('2d')
        context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)
        const imageBase64 = canvas.toDataURL('image/jpeg', 0.8)
        try {
          const response = await detectObjects(imageBase64)
          setResult(response)
          if (response?.detections?.length) {
            const topDetection = response.detections[0]
            setStatus(`Detected ${topDetection.label} at ${topDetection.distance}`)
          } else {
            setStatus('No object detected.')
          }
          setError(null)
        } catch (err) {
          setError('Detection request failed.')
        }
      }, 2000)
    }

    return () => {
      if (intervalId) window.clearInterval(intervalId)
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [isDetecting])

  const toggleDetection = () => {
    setIsDetecting((prev) => !prev)
    setStatus(isDetecting ? 'Stopped detection.' : 'Listening for objects.')
  }

  const toggleLocationSharing = () => {
    setIsSharingLocation((prev) => !prev)
  }

  return (
    <div className={styles.page}>
      <Header />

      <main className={styles.main}>
        <p className={styles.status} aria-live="polite">
          {status}
        </p>

        <div className={styles.videoCard}>
          <video ref={videoRef} className={styles.video} playsInline muted />
        </div>

        <div className={styles.startButtonWrap}>
          {isDetecting ? (
            <>
              <span className={styles.pulseRing} aria-hidden="true" />
              <span
                className={`${styles.pulseRing} ${styles.pulseRingDelay}`}
                aria-hidden="true"
              />
            </>
          ) : null}

          <button
            type="button"
            className={styles.startButton}
            aria-pressed={isDetecting}
            aria-label={
              isDetecting ? 'Stop object detection' : 'Start object detection'
            }
            onClick={toggleDetection}
          >
            {isDetecting ? 'Stop' : 'Start'}
          </button>
        </div>

        {error ? <p className={styles.error}>{error}</p> : null}

        {result?.detections?.length ? (
          <div className={styles.resultBox}>
            <h2 className={styles.resultTitle}>Latest detection</h2>
            {result.detections.map((item, index) => (
              <p key={`${item.label}-${index}`} className={styles.resultText}>
                {item.label} · confidence {Math.round(item.confidence * 100)}% · distance {item.distance}
              </p>
            ))}
          </div>
        ) : null}

        <button
          type="button"
          className={`${styles.locationToggle} ${
            isSharingLocation ? styles.locationToggleActive : ''
          }`}
          aria-pressed={isSharingLocation}
          aria-label={
            isSharingLocation
              ? 'Stop sharing your location'
              : 'Share your location'
          }
          onClick={toggleLocationSharing}
        >
          <MapPin size={18} aria-hidden="true" />
          {isSharingLocation ? 'Sharing location' : 'Share my location'}
        </button>
      </main>

      <Footer />
    </div>
  )
}

export default Home
