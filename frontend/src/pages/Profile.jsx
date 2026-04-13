import { useAuth } from '../context/AuthContext';
import './Profile.css';

export default function Profile() {
  const { user, logout } = useAuth();

  return (
    <div className="profile-page">
      <div className="profile-card animate-fade-in">
        <div className="profile-avatar-large">
          {user?.name?.[0]?.toUpperCase() || 'U'}
        </div>
        <div className="profile-info">
          <h2>{user?.name}</h2>
          <p>{user?.email}</p>
          <p className="profile-joined">
            Member since {user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : '—'}
          </p>
        </div>
      </div>

      <div className="profile-sections">
        <div className="profile-section card">
          <h3>About NOTSY</h3>
          <p>NOTSY is your AI-powered personal knowledge management app. Build notebooks for each subject, upload your study materials, and chat with an AI that's grounded in your own notes.</p>
          <div className="profile-features">
            <div className="feature-item">
              <span>📚</span>
              <div>
                <strong>Notebooks & Topics</strong>
                <p>Organize your knowledge hierarchically</p>
              </div>
            </div>
            <div className="feature-item">
              <span>🤖</span>
              <div>
                <strong>RAG-Powered Chat</strong>
                <p>AI responses grounded in your study materials</p>
              </div>
            </div>
            <div className="feature-item">
              <span>🌿</span>
              <div>
                <strong>Branching Conversations</strong>
                <p>Explore tangents without losing context</p>
              </div>
            </div>
            <div className="feature-item">
              <span>🕸️</span>
              <div>
                <strong>Knowledge Graph</strong>
                <p>Visualize how topics connect</p>
              </div>
            </div>
          </div>
        </div>

        <div className="profile-section card">
          <h3>Account</h3>
          <button className="btn-danger" onClick={logout}>
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
