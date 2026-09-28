import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { RequireAdmin } from './auth/RequireAdmin'
import { RequireAuth } from './auth/RequireAuth'
import { LoginPage } from './pages/LoginPage'
import { CollectionPage } from './pages/CollectionPage'
import { ItemDetailPage } from './pages/ItemDetailPage'
import { ManualEntryPage } from './pages/ManualEntryPage'
import { ScanPage } from './pages/ScanPage'
import { ResolutionPage } from './pages/ResolutionPage'
import { AdminUsersPage } from './pages/AdminUsersPage'
import { AdminItemEditPage } from './pages/AdminItemEditPage'
import { AdminBarcodeCachePage } from './pages/AdminBarcodeCachePage'
import './App.css'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <RequireAuth>
                  <CollectionPage />
                </RequireAuth>
              }
            />
            <Route
              path="/scan"
              element={
                <RequireAuth>
                  <ScanPage />
                </RequireAuth>
              }
            />
            <Route
              path="/resolve/:barcode"
              element={
                <RequireAuth>
                  <ResolutionPage />
                </RequireAuth>
              }
            />
            <Route
              path="/items/new"
              element={
                <RequireAuth>
                  <ManualEntryPage />
                </RequireAuth>
              }
            />
            <Route
              path="/items/:id/edit"
              element={
                <RequireAuth>
                  <ManualEntryPage />
                </RequireAuth>
              }
            />
            <Route
              path="/items/:id"
              element={
                <RequireAuth>
                  <ItemDetailPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin/users"
              element={
                <RequireAdmin>
                  <AdminUsersPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/admin/items/:id"
              element={
                <RequireAdmin>
                  <AdminItemEditPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/admin/barcode-cache"
              element={
                <RequireAdmin>
                  <AdminBarcodeCachePage />
                </RequireAdmin>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
