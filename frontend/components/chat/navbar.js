'use client'
import { useEffect, useRef, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation";
import posthog from "posthog-js";

// utils
import { removeCookie } from "@/utils/cookie";

// components
import Notification from "@/components/chat/notification";
import Setting from "@/components/settings";
import SearchPopup from "@/components/chat/searchPopup";

// context
import { useProjectContext } from "@/context/ProjectContext";

const API_HOST = process.env.API_HOST || "http://localhost:8765/api";

export default function Navbar () {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { project } = useProjectContext();

    const projectId = project?.project?._id || null;

    const activeTab = searchParams.get('tab');

    const popupRef = useRef(null);
    const [profilePopup,setProfilePopup] = useState(false)
    const [menuToggle,setMenuToggle] = useState(false)
    const [notificationPopup,setNotificationPopup] = useState(false)
    const [settingsPopup,setSettingsPopup] = useState(false)
    const [toggleSearchPopup,setToggleSearchPopup] = useState(false)
    const [preSearchResults, setPreSearchResults] = useState([])

    useEffect(() => {
        fetchHistory()
    }, [projectId])

    const fetchHistory = async () => {
        // preload search result once for avoiding delay
        if (!projectId) return
        const res = await fetch(
            `${API_HOST}/user/conversations/search?q=&pid=${projectId}`,
            {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                },
            }
        );
        if (res.ok) {
            const data = await res.json();
            setPreSearchResults(data.results || []);
        }
    }

    useEffect(() => {
        function handleClickOutside(event) {
            const searchPopup = document.querySelector('.searchPopup_wrap')
            
            if (popupRef.current && !popupRef.current.contains(event.target)) {
                setProfilePopup(false);
            }

            if (searchPopup && !searchPopup.contains(event.target)) {
                setToggleSearchPopup(false);
            }
        }

        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    useEffect(() => {
        if (menuToggle) {
            document.documentElement.style.overflowY = 'hidden';
        } else {
            document.documentElement.style.overflowY = 'auto';
        }
    }, [menuToggle]);

    useEffect(() => {
        setNotificationPopup(false)
        if(settingsPopup || toggleSearchPopup ) {
            document.documentElement.style.overflow = "clip"
        } else {
            document.documentElement.style.overflow = "auto"
        }
    },[settingsPopup, toggleSearchPopup])

    const togglePopup = () => {
        setMenuToggle(!menuToggle)
    }

    const logout = () => {
        removeCookie("access_token")
        removeCookie("session_id")
        window.location.reload();
        posthog.reset();
    }

    const navigateSection = (tab) => {
        if (tab === activeTab) return
        router.push(`/chat?tab=${tab}`)
        setMenuToggle(false)
    }

    const goHome = () => {
        router.push(`/chat?tab=insights`)
    }

    const goToHelp = () => {
        window.open('/help', '_blank');
    }

    return ( 
        <div className="navbar_container">
            <div className="navbar_left">
                <svg className="statement-logo" onClick={() => goHome()}  xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 52 52" fill="none">
                    <path d="M19.5836 18.5209H31.3498M19.5836 24.255H31.3498M19.5836 29.9883H31.3498M14 38.8634V15.598C14 13.6108 15.9046 12 18.2545 12H32.7463C35.0954 12 37 13.6108 37 15.598V38.8681C37 39.083 36.7264 39.218 36.5052 39.1125L31.6093 36.7824C31.5097 36.735 31.389 36.7343 31.2886 36.78L25.8187 39.2785C25.7231 39.3228 25.6086 39.3235 25.5114 39.2824L19.6102 36.7738C19.5107 36.7319 19.393 36.7343 19.2958 36.7816L14.4979 39.107C14.276 39.2149 14 39.0791 14 38.8634Z" stroke="#48C884" strokeWidth="2.82872" strokeLinecap="round"/>
                </svg>
                <div className="nabar_sections">
                    <a className={`nabar_sections_wrapper ${activeTab === "insights" ? '_active': ''}`} onClick={() => navigateSection('insights')}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
                            <path d="M12 1.5H6C3 1.5 1.5 3 1.5 6V15.75C1.5 16.1625 1.8375 16.5 2.25 16.5H12C15 16.5 16.5 15 16.5 12V6C16.5 3 15 1.5 12 1.5Z" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M5.25 7.125H12.75" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M5.25 10.875H10.5" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        Notes & Insight
                    </a>
                    <a className={`nabar_sections_wrapper ${activeTab === "chat" ? '_active': ''}`} onClick={() => navigateSection('chat')}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
                            <path d="M6.375 14.25H6C3 14.25 1.5 13.5 1.5 9.75V6C1.5 3 3 1.5 6 1.5H12C15 1.5 16.5 3 16.5 6V9.75C16.5 12.75 15 14.25 12 14.25H11.625C11.3925 14.25 11.1675 14.3625 11.025 14.55L9.9 16.05C9.405 16.71 8.595 16.71 8.1 16.05L6.975 14.55C6.855 14.385 6.5775 14.25 6.375 14.25Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M5.25 6H12.75" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M5.25 9.75H9.75" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        Chat
                    </a>
                    <a className={`nabar_sections_wrapper ${activeTab === "history" ? '_active': ''}`} onClick={() => navigateSection('history')}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
                            <path d="M13.485 8.09251V11.0925C13.485 11.2875 13.4775 11.475 13.455 11.655C13.2825 13.68 12.09 14.685 9.8925 14.685H9.59251C9.40501 14.685 9.225 14.775 9.1125 14.925L8.21251 16.125C7.81501 16.6575 7.17 16.6575 6.7725 16.125L5.87249 14.925C5.77499 14.7975 5.5575 14.685 5.3925 14.685H5.09251C2.70001 14.685 1.5 14.0925 1.5 11.0925V8.09251C1.5 5.89501 2.51251 4.70251 4.53001 4.53001C4.71001 4.50751 4.89751 4.5 5.09251 4.5H9.8925C12.285 4.5 13.485 5.70001 13.485 8.09251Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M16.4863 5.09251V8.09251C16.4863 10.2975 15.4737 11.4825 13.4562 11.655C13.4787 11.475 13.4863 11.2875 13.4863 11.0925V8.09251C13.4863 5.70001 12.2862 4.5 9.89375 4.5H5.09375C4.89875 4.5 4.71125 4.50751 4.53125 4.53001C4.70375 2.51251 5.89625 1.5 8.09375 1.5H12.8937C15.2862 1.5 16.4863 2.70001 16.4863 5.09251Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M10.1216 9.9375H10.1284" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M7.49662 9.9375H7.50337" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M4.87162 9.9375H4.87837" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        History
                    </a>
                </div>
            </div>
            <div className="navbar_right">
                <div className="navbar_right_search">
                    <div className="dummy_input" onClick={() => setToggleSearchPopup(!toggleSearchPopup)} >
                        <img className="search_icon" src="/next_images/search.svg"/>   
                        Search
                    </div>
                    {/* <input placeholder="Search" />  */}
                    {toggleSearchPopup && (
                        <SearchPopup closeMenu={() => setToggleSearchPopup(false)} history={preSearchResults}/>
                    )}
                </div>
                <div className={`navbar_notification ${notificationPopup ? '_active': ''}`} onClick={() => setNotificationPopup(!notificationPopup)}>
                    <img className="icon" src="/next_images/bell.svg"  />
                    {notificationPopup && (
                        <Notification onClose={() => setNotificationPopup(!notificationPopup)}/>
                    )}
                </div>
                <div className="navbar_settings" onClick={() => setSettingsPopup(!settingsPopup)}>
                    <img className="icon" src="/next_images/settings.svg"  />
                    {settingsPopup && (
                        <Setting onClose={() => setSettingsPopup(!settingsPopup)} />
                    )}
                </div>
                <div className="navbar_profile_wrap">
                    <img className="navbar_profile" src="/next_images/avatar.svg" onClick={() => setProfilePopup(!profilePopup)} />
                    {profilePopup &&
                        <div className="navbar_profile_popup" ref={popupRef}>
                            <div onClick={logout}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                                    <path d="M17.4375 14.62L19.9975 12.06L17.4375 9.5" stroke="#ABABAB" strokeWidth="1.5" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M9.75781 12.0586H19.9278" stroke="#ABABAB" strokeWidth="1.5" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M11.7578 20C7.33781 20 3.75781 17 3.75781 12C3.75781 7 7.33781 4 11.7578 4" stroke="#ABABAB" strokeWidth="1.5" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                                Log out
                            </div>
                            <div onClick={() => goToHelp()}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                                    <path d="M12 22C17.5 22 22 17.5 22 12C22 6.5 17.5 2 12 2C6.5 2 2 6.5 2 12C2 17.5 6.5 22 12 22Z" stroke="#ABABAB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M12 8V13" stroke="#ABABAB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M11.9922 16H12.0012" stroke="#ABABAB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                                Help
                            </div>
                        </div>
                    }
                </div>
            </div>
            <div className="hamburger_icon">
                <img src={`/next_images/${!menuToggle? 'hamburger': 'close'}.svg`} onClick={() => togglePopup()}/>
                {menuToggle && (
                    <div className="hamburger_menu">
                        <div className="navbar_right_search nabar_sections_wrapper">
                            <input placeholder="Search"/> 
                            <img src="/next_images/search.svg"/>   
                        </div>
                        <a className="nabar_sections_wrapper" onClick={() => navigateSection('insights')} >
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
                                <path d="M12 1.5H6C3 1.5 1.5 3 1.5 6V15.75C1.5 16.1625 1.8375 16.5 2.25 16.5H12C15 16.5 16.5 15 16.5 12V6C16.5 3 15 1.5 12 1.5Z" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M5.25 7.125H12.75" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M5.25 10.875H10.5" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            Notes & Insight
                        </a>
                        <a className="nabar_sections_wrapper" onClick={() => navigateSection('chat')} >
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
                                <path d="M6.375 14.25H6C3 14.25 1.5 13.5 1.5 9.75V6C1.5 3 3 1.5 6 1.5H12C15 1.5 16.5 3 16.5 6V9.75C16.5 12.75 15 14.25 12 14.25H11.625C11.3925 14.25 11.1675 14.3625 11.025 14.55L9.9 16.05C9.405 16.71 8.595 16.71 8.1 16.05L6.975 14.55C6.855 14.385 6.5775 14.25 6.375 14.25Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M5.25 6H12.75" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M5.25 9.75H9.75" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            Chat
                        </a>
                        <a className="nabar_sections_wrapper" onClick={() => navigateSection('history')}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
                                <path d="M13.485 8.09251V11.0925C13.485 11.2875 13.4775 11.475 13.455 11.655C13.2825 13.68 12.09 14.685 9.8925 14.685H9.59251C9.40501 14.685 9.225 14.775 9.1125 14.925L8.21251 16.125C7.81501 16.6575 7.17 16.6575 6.7725 16.125L5.87249 14.925C5.77499 14.7975 5.5575 14.685 5.3925 14.685H5.09251C2.70001 14.685 1.5 14.0925 1.5 11.0925V8.09251C1.5 5.89501 2.51251 4.70251 4.53001 4.53001C4.71001 4.50751 4.89751 4.5 5.09251 4.5H9.8925C12.285 4.5 13.485 5.70001 13.485 8.09251Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M16.4863 5.09251V8.09251C16.4863 10.2975 15.4737 11.4825 13.4562 11.655C13.4787 11.475 13.4863 11.2875 13.4863 11.0925V8.09251C13.4863 5.70001 12.2862 4.5 9.89375 4.5H5.09375C4.89875 4.5 4.71125 4.50751 4.53125 4.53001C4.70375 2.51251 5.89625 1.5 8.09375 1.5H12.8937C15.2862 1.5 16.4863 2.70001 16.4863 5.09251Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M10.1216 9.9375H10.1284" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M7.49662 9.9375H7.50337" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M4.87162 9.9375H4.87837" stroke="#9D9D9D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            History
                        </a>
                        <div className="nabar_sections_wrapper">
                            <svg xmlns="http://www.w3.org/2000/svg" width="21" height="22" viewBox="0 0 21 22" fill="none">
                                <path d="M15.875 7.58203C15.875 6.2228 15.335 4.91923 14.3739 3.95811C13.4128 2.99699 12.1092 2.45703 10.75 2.45703C9.39077 2.45703 8.0872 2.99699 7.12608 3.95811C6.16495 4.91923 5.625 6.2228 5.625 7.58203C5.625 13.5612 3.0625 15.2695 3.0625 15.2695H18.4375C18.4375 15.2695 15.875 13.5612 15.875 7.58203Z" stroke="#9D9D9D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M12.2289 18.6875C12.0787 18.9464 11.8631 19.1613 11.6038 19.3106C11.3445 19.46 11.0504 19.5386 10.7511 19.5386C10.4519 19.5386 10.1578 19.46 9.89849 19.3106C9.63915 19.1613 9.42361 18.9464 9.27344 18.6875" stroke="#9D9D9D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            Notification
                        </div>
                        <div className="nabar_sections_wrapper">
                            <svg xmlns="http://www.w3.org/2000/svg" width="21" height="22" viewBox="0 0 21 22" fill="none">
                                <g clipPath="url(#clip0_5940_26167)">
                                <path d="M10.25 13.5625C11.6652 13.5625 12.8125 12.4152 12.8125 11C12.8125 9.58477 11.6652 8.4375 10.25 8.4375C8.83477 8.4375 7.6875 9.58477 7.6875 11C7.6875 12.4152 8.83477 13.5625 10.25 13.5625Z" stroke="#9D9D9D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M16.5682 13.5638C16.4545 13.8214 16.4206 14.1072 16.4708 14.3843C16.5211 14.6614 16.6532 14.9171 16.8501 15.1184L16.9014 15.1696C17.0602 15.3283 17.1862 15.5167 17.2722 15.7241C17.3581 15.9315 17.4024 16.1538 17.4024 16.3783C17.4024 16.6028 17.3581 16.8251 17.2722 17.0325C17.1862 17.2399 17.0602 17.4283 16.9014 17.5869C16.7427 17.7458 16.5543 17.8718 16.3469 17.9577C16.1395 18.0437 15.9172 18.088 15.6927 18.088C15.4682 18.088 15.2459 18.0437 15.0385 17.9577C14.8311 17.8718 14.6427 17.7458 14.4841 17.5869L14.4328 17.5357C14.2315 17.3388 13.9758 17.2067 13.6987 17.1564C13.4216 17.1062 13.1359 17.1401 12.8782 17.2538C12.6256 17.3621 12.4101 17.5419 12.2584 17.771C12.1066 18.0002 12.0252 18.2687 12.0241 18.5436V18.6888C12.0241 19.1419 11.8441 19.5764 11.5237 19.8968C11.2033 20.2171 10.7688 20.3971 10.3157 20.3971C9.86265 20.3971 9.42813 20.2171 9.10775 19.8968C8.78738 19.5764 8.6074 19.1419 8.6074 18.6888V18.6119C8.60078 18.3292 8.50927 18.055 8.34475 17.825C8.18023 17.595 7.95032 17.4198 7.6849 17.3221C7.42727 17.2084 7.14148 17.1745 6.86439 17.2248C6.58731 17.275 6.33162 17.4071 6.13031 17.604L6.07906 17.6553C5.9204 17.8141 5.73199 17.9401 5.52461 18.0261C5.31722 18.112 5.09492 18.1563 4.87042 18.1563C4.64591 18.1563 4.42362 18.112 4.21623 18.0261C4.00884 17.9401 3.82043 17.8141 3.66177 17.6553C3.50294 17.4966 3.37693 17.3082 3.29096 17.1008C3.20499 16.8934 3.16074 16.6711 3.16074 16.4466C3.16074 16.2221 3.20499 15.9998 3.29096 15.7924C3.37693 15.585 3.50294 15.3966 3.66177 15.238L3.71302 15.1867C3.90994 14.9854 4.04203 14.7297 4.09227 14.4526C4.14252 14.1755 4.1086 13.8898 3.9949 13.6321C3.88662 13.3795 3.70683 13.164 3.47767 13.0123C3.2485 12.8605 2.97996 12.7791 2.7051 12.778H2.5599C2.10682 12.778 1.6723 12.598 1.35192 12.2776C1.03155 11.9572 0.851563 11.5227 0.851562 11.0696C0.851562 10.6166 1.03155 10.182 1.35192 9.86166C1.6723 9.54129 2.10682 9.3613 2.5599 9.3613H2.63677C2.9195 9.35469 3.19369 9.26317 3.42371 9.09865C3.65374 8.93414 3.82894 8.70422 3.92656 8.4388C4.04026 8.18117 4.07418 7.89539 4.02394 7.6183C3.9737 7.34121 3.8416 7.08553 3.64469 6.88422L3.59344 6.83297C3.4346 6.67431 3.3086 6.4859 3.22263 6.27851C3.13666 6.07112 3.09241 5.84882 3.09241 5.62432C3.09241 5.39982 3.13666 5.17752 3.22263 4.97013C3.3086 4.76274 3.4346 4.57434 3.59344 4.41568C3.7521 4.25684 3.94051 4.13084 4.14789 4.04487C4.35528 3.9589 4.57758 3.91465 4.80208 3.91465C5.02658 3.91465 5.24888 3.9589 5.45627 4.04487C5.66366 4.13084 5.85207 4.25684 6.01073 4.41568L6.06198 4.46693C6.26329 4.66384 6.51897 4.79594 6.79606 4.84618C7.07315 4.89642 7.35893 4.8625 7.61656 4.7488H7.6849C7.93753 4.64053 8.15299 4.46074 8.30476 4.23157C8.45652 4.00241 8.53797 3.73387 8.53906 3.45901V3.3138C8.53906 2.86072 8.71905 2.4262 9.03942 2.10583C9.3598 1.78545 9.79432 1.60547 10.2474 1.60547C10.7005 1.60547 11.135 1.78545 11.4554 2.10583C11.7757 2.4262 11.9557 2.86072 11.9557 3.3138V3.39068C11.9568 3.66554 12.0383 3.93408 12.19 4.16324C12.3418 4.39241 12.5573 4.57219 12.8099 4.68047C13.0675 4.79417 13.3533 4.82809 13.6304 4.77785C13.9075 4.72761 14.1632 4.59551 14.3645 4.39859L14.4157 4.34734C14.5744 4.18851 14.7628 4.0625 14.9702 3.97653C15.1776 3.89056 15.3999 3.84631 15.6244 3.84631C15.8489 3.84631 16.0712 3.89056 16.2786 3.97653C16.486 4.0625 16.6744 4.18851 16.833 4.34734C16.9919 4.506 17.1179 4.69441 17.2038 4.9018C17.2898 5.10919 17.3341 5.33149 17.3341 5.55599C17.3341 5.78049 17.2898 6.00279 17.2038 6.21018C17.1179 6.41757 16.9919 6.60598 16.833 6.76464L16.7818 6.81589C16.5849 7.01719 16.4528 7.27288 16.4025 7.54997C16.3523 7.82705 16.3862 8.11284 16.4999 8.37047V8.4388C16.6082 8.69144 16.788 8.9069 17.0171 9.05866C17.2463 9.21043 17.5148 9.29187 17.7897 9.29297H17.9349C18.388 9.29297 18.8225 9.47295 19.1429 9.79333C19.4632 10.1137 19.6432 10.5482 19.6432 11.0013C19.6432 11.4544 19.4632 11.8889 19.1429 12.2093C18.8225 12.5296 18.388 12.7096 17.9349 12.7096H17.858C17.5832 12.7107 17.3146 12.7922 17.0855 12.9439C16.8563 13.0957 16.6765 13.3112 16.5682 13.5638V13.5638Z" stroke="#9D9D9D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                </g>
                                <defs>
                                <clipPath id="clip0_5940_26167">
                                <rect width="20.5" height="20.5" fill="white" transform="translate(0 0.75)"/>
                                </clipPath>
                                </defs>
                            </svg>
                            Settings
                        </div>
                        <div className="nabar_sections_wrapper logout" onClick={logout}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                                <path d="M17.4375 14.62L19.9975 12.06L17.4375 9.5" stroke="#ABABAB" strokeWidth="1.5" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M9.75781 12.0586H19.9278" stroke="#ABABAB" strokeWidth="1.5" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M11.7578 20C7.33781 20 3.75781 17 3.75781 12C3.75781 7 7.33781 4 11.7578 4" stroke="#ABABAB" strokeWidth="1.5" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            Log out
                        </div>
                        <div className="nabar_sections_wrapper" onClick={() => goToHelp()}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                                <path d="M12 22C17.5 22 22 17.5 22 12C22 6.5 17.5 2 12 2C6.5 2 2 6.5 2 12C2 17.5 6.5 22 12 22Z" stroke="#ABABAB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M12 8V13" stroke="#ABABAB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M11.9922 16H12.0012" stroke="#ABABAB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            Help
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}