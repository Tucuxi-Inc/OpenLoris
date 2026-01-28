import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/user/DashboardPage'
import AskQuestionPage from './pages/user/AskQuestionPage'
import QuestionDetailPage from './pages/user/QuestionDetailPage'
import ExpertDashboard from './pages/expert/ExpertDashboard'
import ExpertQueuePage from './pages/expert/ExpertQueuePage'
import ExpertQuestionDetail from './pages/expert/ExpertQuestionDetail'
import KnowledgeManagementPage from './pages/expert/KnowledgeManagementPage'
import DocumentManagementPage from './pages/expert/DocumentManagementPage'
import UserManagementPage from './pages/admin/UserManagementPage'
import NotificationsPage from './pages/NotificationsPage'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          {/* Business user routes */}
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="ask" element={<AskQuestionPage />} />
          <Route path="questions/:questionId" element={<QuestionDetailPage />} />
          {/* Expert routes */}
          <Route path="expert" element={<ExpertDashboard />} />
          <Route path="expert/queue" element={<ExpertQueuePage />} />
          <Route path="expert/questions/:questionId" element={<ExpertQuestionDetail />} />
          <Route path="expert/knowledge" element={<KnowledgeManagementPage />} />
          <Route path="expert/documents" element={<DocumentManagementPage />} />
          {/* Notifications */}
          <Route path="notifications" element={<NotificationsPage />} />
          {/* Admin routes */}
          <Route path="admin/users" element={<UserManagementPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}

export default App
