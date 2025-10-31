import {Route, Routes, Navigate, useLocation} from 'react-router-dom'
import Landing from './pages/Landing'
import DemoOCR from './pages/DemoOCR'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Docs from './pages/Docs'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import ProtectedRoute from './auth/ProtectedRoute'
import {AuthProvider} from './auth/auth-context'

export default function App() {
    const location = useLocation()
    // Hide navbar only on root route which redirects to /home
    const hideNavbar = false

    return (
        <AuthProvider>
            <div className="min-h-screen flex flex-col">
                {!hideNavbar && <Navbar/>}
                <main className="flex-1">
                    <Routes>
                        <Route path="/" element={<Navigate to="/home" replace/>}/>
                        <Route path="/home" element={<Landing/>}/>

                        {/* keep other routes as-is */}
                        <Route path="/demo" element={<DemoOCR/>}/>
                        <Route path="/login" element={<Login/>}/>
                        <Route path="/docs" element={<Docs/>}/>
                        <Route
                            path="/dashboard"
                            element={
                                <ProtectedRoute>
                                    <Dashboard/>
                                </ProtectedRoute>
                            }
                        />
                        <Route path="*" element={<Navigate to="/home"/>}/>
                    </Routes>
                </main>
                <Footer/>
            </div>
        </AuthProvider>
    )
}
