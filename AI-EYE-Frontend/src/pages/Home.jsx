import { useState } from 'react'
import { MapPin } from 'lucide-react'
import Footer from '../components/Footer.jsx'
import Header from '../components/Header.jsx'
import styles from './Home.module.css'

function Home() {
  const [isDetecting, setIsDetecting] = useState(false)
  const [isSharingLocation, setIsSharingLocation] = useState(false)

  const toggleDetection = () => {
    setIsDetecting((prev) => !prev)
  }

  const toggleLocationSharing = () => {
    setIsSharingLocation((prev) => !prev)
  }

  return (
    <div className={styles.page}>
      <Header />

      <main className={styles.main}>
        <p className={styles.status} aria-live="polite">
          {isDetecting
            ? 'Listening for objects.'
            : 'Ready. Double tap start to begin.'}
        </p>

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
