'use client'
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function Header () {    
    const [scrolled, setScrolled] = useState(false);
    const [showMenu, setShowhowMenu] = useState(false);
    const router = useRouter();

    useEffect(() => {
        const handleScroll = () => {

            if (window.scrollY > 0) {
                setScrolled(true);
            }

            if (window.scrollY == 0) {
                setScrolled(false)
            }
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const scrollToSection = (sectionId, e) => {
        e.preventDefault();
        const section = document.getElementById(sectionId);
        if (section) {
            const yOffset = -120;
            const y = section.getBoundingClientRect().top + window.pageYOffset + yOffset;
            window.scrollTo({ top: y, behavior: 'smooth' });
        }
        openMenu()
    }

    const openMenu = () => {
        setShowhowMenu(!showMenu)
    }


    return (
        <>
            {scrolled && <div style={{ height: '104.31px' }}></div>} 
            <div className={`header ${scrolled ? 'scrolled': ''}`}>
                <div className="header_wrap">
                    <div className="logo_wrap" onClick={() => router.push('/')}>
                        <img className="logo" src="/next_images/logo.svg"/>
                        <h1>Statement</h1>
                    </div>
                    <div className="header_menu">
                        <Link href="/">Home</Link>
                    </div>
                    <div className="header_button">
                        
                        <Link href="/login"><button>Log in</button></Link>
                        <Link href="/signup"><button className="sign_up">Signup</button></Link>
                    </div>
                    {showMenu ? 
                        <svg xmlns="http://www.w3.org/2000/svg" width="27" height="27" viewBox="0 0 27 27" fill="none" className="hamburger_menu" onClick={openMenu}>
                            <rect y="24.749" width="35" height="2" transform="rotate(-45 0 24.749)" fill="white"/>
                            <rect x="2.25" width="35" height="2" transform="rotate(45 2.25 0)" fill="white"/>
                        </svg> :
                        <svg xmlns="http://www.w3.org/2000/svg" width="35" height="18" viewBox="0 0 35 18" fill="none" className="hamburger_menu" onClick={openMenu}>
                            <rect width="35" height="2" fill="white" fillOpacity="0.87" />
                            <rect y="8" width="35" height="2" fill="white" fillOpacity="0.87"/>
                            <rect y="16" width="35" height="2" fill="white" fillOpacity="0.87"/>
                        </svg> }
                </div>
                <div className={`mobile_menu ${showMenu? 'visible' : ''}`}>
                    <Link href="/">Home</Link>
                </div>
            </div>

        </>
    )
}