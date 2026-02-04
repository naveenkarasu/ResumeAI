import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout';
import { ToastContainer, ErrorBoundary } from './components/ui';
import { ChatPage, JobMatchPage, AnalyzerPage, InterviewPage, EmailPage, SettingsPage } from './pages';
import JobListPage from './pages/JobListPage';

function App() {
  return (
    <ErrorBoundary>
      <Layout>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/jobs" element={<JobMatchPage />} />
          <Route path="/job-list" element={<JobListPage />} />
          <Route path="/analyzer" element={<AnalyzerPage />} />
          <Route path="/interview" element={<InterviewPage />} />
          <Route path="/email" element={<EmailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
      <ToastContainer />
    </ErrorBoundary>
  );
}

export default App;
