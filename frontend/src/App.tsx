import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/user/DashboardPage'
import AskQuestionPage from './pages/user/AskQuestionPage'
import ExpertQueuePage from './pages/expert/ExpertQueuePage'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="ask" element={<AskQuestionPage />} />
          <Route path="expert/queue" element={<ExpertQueuePage />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}

export default App
