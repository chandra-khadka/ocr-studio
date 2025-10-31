import {Link, NavLink} from 'react-router-dom'
import {useAuth} from '../auth/auth-context'
import {FaRobot} from 'react-icons/fa'
import {useEffect, useState} from 'react'

export default function Navbar() {
    const {isAuthenticated, logout, user} = useAuth()
    const [scrolled, setScrolled] = useState(false)

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 8)
        onScroll()
        window.addEventListener('scroll', onScroll, {passive: true})
        return () => window.removeEventListener('scroll', onScroll)
    }, [])

    return (
        <header
            className={`sticky top-0 z-50 border-b transition-all ${
                scrolled
                    ? 'bg-white/80 backdrop-blur-md shadow-sm'
                    : 'bg-white'
            }`}
        >
            <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
                <Link to="/" className="flex items-center gap-2">
                    <div
                        className="w-10 h-10 rounded-xl bg-primary-light flex items-center justify-center text-primary">
                        <FaRobot size={20}/>
                    </div>
                    <div className="font-extrabold text-xl text-primary">
                        Visionary AI OCR Studio
                    </div>
                </Link>

                <nav className="flex items-center gap-6">
                    <NavLink
                        to="/demo"
                        className={({isActive}) =>
                            isActive
                                ? 'text-primary font-semibold'
                                : 'text-gray-600 hover:text-primary'
                        }
                    >
                        Demo
                    </NavLink>
                    <NavLink
                        to="/docs"
                        className={({isActive}) =>
                            isActive
                                ? 'text-primary font-semibold'
                                : 'text-gray-600 hover:text-primary'
                        }
                    >
                        Docs
                    </NavLink>
                    <NavLink
                        to="/#pricing"
                        className={({isActive}) =>
                            isActive ? 'text-primary font-semibold' : 'text-gray-600 hover:text-primary'
                        }
                    >
                        Pricing
                    </NavLink>


                    {isAuthenticated ? (
                        <>
                            <NavLink
                                to="/dashboard"
                                className={({isActive}) =>
                                    isActive
                                        ? 'text-primary font-semibold'
                                        : 'text-gray-600 hover:text-primary'
                                }
                            >
                                Dashboard
                            </NavLink>
                            <div className="text-sm text-gray-500 hidden md:block">
                                Signed in as <span className="font-semibold">{user?.email}</span>
                            </div>
                            <button className="btn-outline" onClick={logout}>Logout</button>
                        </>
                    ) : (
                        <NavLink
                            to="/login"
                            className={({isActive}) =>
                                isActive ? 'text-primary font-semibold' : 'btn'
                            }
                        >
                            Login
                        </NavLink>
                    )}
                </nav>
            </div>
        </header>
    )
}
