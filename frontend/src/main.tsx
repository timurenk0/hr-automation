import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import Header from './COMPONENTS/Header'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <div className="h-screen w-screen overflow-x-hidden">
        <Header />
        <main className="flex-1 px-4 py-2 w-full min-h-0 overflow-hidden">
          <App />
        </main>
      </div>
    </QueryClientProvider>
  </StrictMode>,
)
