import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import Login from './pages/Login';
import './index.css'

function App() {
  return (
    <Router>
      <Toaster richColors />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/library" element={<div className="text-white">Library Page</div>} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

export default App;