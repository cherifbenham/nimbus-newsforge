import { BrowserRouter } from 'react-router-dom';
import { NewsletterProvider } from './context/NewsletterContext'
import AppRoutes from './routes/AppRoutes'
import './App.css'
import Header from './components/Header';

function App() {


  return (
    <BrowserRouter>
      <NewsletterProvider>
        <div className='flex flex-col h-screen'>
          <Header />
          <AppRoutes />
        </div>
      </NewsletterProvider>
    </BrowserRouter>
  )
}

export default App
