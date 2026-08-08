import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import Header from '../components/Header.jsx'
import Loader from '../components/Loader.jsx'
import { ProfileCard, ProfileSection } from '../components/ProfileCard.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import styles from './Profile.module.css'

function Profile() {
  const { user } = useAuth()

  if (!user) {
    return (
      <div className={styles.page}>
        <Header />
        <main className={styles.main}>
          <div className={styles.loaderWrap}>
            <Loader label="Loading profile" />
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <Header />

      <main className={styles.main}>
        <Link to="/home" className={styles.backLink} aria-label="Back to home">
          <ArrowLeft size={20} aria-hidden="true" />
        </Link>

        <h1 className={styles.pageTitle}>Your profile</h1>

        <div className={styles.sections}>
          <ProfileSection title="Personal details">
            <ProfileCard label="Full name" value={user.fullName} />
            <ProfileCard label="Username" value={user.username} />
            <ProfileCard label="Age" value={user.age} />
            <ProfileCard label="Gender" value={user.gender} />
            <ProfileCard label="Contact number" value={user.contactNo} />
            <ProfileCard label="Email" value={user.email} />
            <ProfileCard label="Address" value={user.address} />
          </ProfileSection>

          <ProfileSection title="Accessibility details">
            <ProfileCard
              label="Visual impairment type"
              value={user.visualImpairmentType}
            />
            <ProfileCard
              label="Assistance preference"
              value={user.assistancePreference}
            />
            <ProfileCard
              label="Preferred language"
              value={user.preferredLanguage}
            />
            <ProfileCard
              label="Certificate file name"
              value={user.certificateFileName}
            />
          </ProfileSection>

          <ProfileSection title="Emergency contact">
            <ProfileCard
              label="Emergency contact name"
              value={user.emergencyContactName}
            />
            <ProfileCard
              label="Emergency contact number"
              value={user.emergencyContactNo}
            />
          </ProfileSection>
        </div>
      </main>
    </div>
  )
}

export default Profile
