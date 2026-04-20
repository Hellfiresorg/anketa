import { BrowserRouter, Route, Routes } from 'react-router-dom'
import SurveyPage from './pages/Survey'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/s/:invitationId" element={<SurveyPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
