'use client'
import { useRef, useState, useEffect } from "react"
import { useSearchParams } from "next/navigation";

import '@/style/component/settings.scss';

// components
import ApiScreen from "@/components/settings/api";
import TwoFactorAuth from "@/components/settings/twoFactorAuth";

// utils
import { clearSessionCookies } from "@/utils/cookie";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

// Hardcoded currency and timezone options
const CURRENCIES = [
    { value: 'USD', label: 'USD $' },
    { value: 'EUR', label: 'EUR €' },
    { value: 'GBP', label: 'GBP £' },
    { value: 'JPY', label: 'JPY ¥' },
    { value: 'CAD', label: 'CAD C$' },
    { value: 'AUD', label: 'AUD A$' },
    { value: 'CHF', label: 'CHF Fr' },
    { value: 'CNY', label: 'CNY ¥' },
    { value: 'INR', label: 'INR ₹' }
];

const TIMEZONES = [
    { value: 'GMT+0', label: 'London, UK (GMT +0:00)' },
    { value: 'GMT+1', label: 'Berlin, Germany (GMT +1:00)' },
    { value: 'GMT-5', label: 'New York, USA (GMT -5:00)' },
    { value: 'GMT-8', label: 'Los Angeles, USA (GMT -8:00)' },
    { value: 'GMT+9', label: 'Tokyo, Japan (GMT +9:00)' },
    { value: 'GMT+5:30', label: 'Mumbai, India (GMT +5:30)' },
    { value: 'GMT+8', label: 'Singapore (GMT +8:00)' },
    { value: 'GMT+2', label: 'Cairo, Egypt (GMT +2:00)' }
];

export default function Setting ({onClose}) {

    const [editInput,setEditInput] = useState(false)
    const [editCompanyName, setEditCompanyName] = useState(false)
    const [editCompanyAddress, setEditCompanyAddress] = useState(false)
    const [draftName, setDraftName] = useState("");     
    const [currentPassword, setCurrentPassword] = useState("");     
    const [newPassword, setNewPassword] = useState("");     
    const [draftCompanyName, setDraftCompanyName] = useState("");     
    const [draftCompanyAddress, setDraftCompanyAddress] = useState("");     
    const [changedField, setChangedField] = useState("");   
    const [showPopup, setShowPopup] = useState(false) 
    const [editEmail, setEditEmail] = useState(false)
    const [changePassword, setChangePassword] = useState(false)
    const [showSaveButton, setShowsaveButton] = useState(false)
    const [draftEmail, setDraftEmail] = useState("");
    const [hidePassword, setHidePassword] = useState(true);
    const [hidePasswordVerify, setHidePasswordVerify] = useState(true);
    const [isDeletingProfile, setIsDeletingProfile] = useState(false);
    const [settingsDropdown, setSettingsDropdown] = useState("Profile");    
    const [passwordConfirm, setPasswordConfirm] = useState(false)
    const [show2faPopup, setShow2faPopup] = useState(false)
    const [activityData, setActivityData] = useState({
        currentSessions: [],
        recentActivity: []
    });
    
    const [profileData, setProfileData] = useState({
        fullname: "",
        email: "",
        companyname: "",
        companyaddress: "",
        currency: "USD",
        timezone: "GMT+0"
    });
    const [formData, setFormData] = useState({
        street: "",
        city: "",
        state: "",
        postcode: ""
    });
    const searchParams = useSearchParams();
    const unsubscribe = searchParams.has('unsubscribe');


    const timeoutRef = useRef(null);
    const menuRef = useRef(null);
    const toggleRef = useRef(null);


    useEffect(() => {
        if (unsubscribe) {
            switchSettings("notification");
        }
    }, [unsubscribe]);

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (
                menuRef.current &&
                !menuRef.current.contains(e.target) &&
                toggleRef.current &&
                !toggleRef.current.contains(e.target)
            ) {
                menuRef.current.classList.remove("show");
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleFormChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
        checkTyped();
    };

    const saveChange = async (field) => {
        try {
            if(field == "fullname") {
                await handleProfileUpdate({ fullname: draftName });
                setProfileData(prev => ({ ...prev, fullname: draftName })); 
                setEditInput(false)
                setChangedField("Full Name")
            } else if (field == "password") {
                await handlePasswordChange({ newPassword: newPassword, currentPassword: currentPassword });
                setChangePassword(false)
                setChangedField("Password")
            } else if (field == "email") {
                await handleProfileUpdate({ email: draftEmail });
                setProfileData(prev => ({ ...prev, email: draftEmail }));
                setEditEmail(false);
                setChangedField("Email Address");
            } else if (field == "companyname") {
                await handleProfileUpdate({ companyname: draftCompanyName });
                setProfileData(prev => ({ ...prev, companyname: draftCompanyName }));
                setEditCompanyName(false);
                setChangedField("Company Name");
            } else if (field == "companyaddress") {
                await handleProfileUpdate({ companyaddress: draftCompanyAddress });
                setProfileData(prev => ({ ...prev, companyaddress: draftCompanyAddress }));
                setEditCompanyAddress(false);
                setChangedField("Company Address");
            } else if (field === "address") {
                await handleProfileUpdate(formData);
                setShowsaveButton(false);
                setChangedField("Company Address");
            } 
            
            setShowPopup(true);

            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }

            timeoutRef.current = setTimeout(() => {
                setShowPopup(false);
            },4000)
        } catch (error) {
            console.error('Error saving changes:', error);
        }
    }

    const switchSettings = (id) => {
        const selected = document.querySelectorAll(".settings_tab")
        selected.forEach((tab) => tab.classList.remove("selected"))
        const selectedTab = document.querySelector(`#${id}-tab`)
        selectedTab.classList.add("selected");

        const sections = document.querySelectorAll(".settings_section")
        sections.forEach(section => section.style.display = "none")

        document.querySelector(`#${id}`).style.display = "block"
        setSettingsDropdown(selectedTab.textContent)
        document.querySelector(".settings_menu_wrap").classList.toggle("show")
    }

    const handleProfileUpdate = async (updateData) => {
        const res = await fetch(`${API_HOST}/settings/profile`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(updateData),
        });

        if (!res.ok) {
            throw new Error('Failed to update profile');
        }
        
        return res.json();
    };

    const handlePasswordChange = async (passwordUpdateData) => {
        const res = await fetch(`${API_HOST}/settings/password`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
            },
            body: JSON.stringify(passwordUpdateData),
        });

        if (!res.ok) {
            throw new Error('Failed to update password');
        } else {
            setNewPassword("")
            setCurrentPassword("")
            setProfileData(prev => ({ ...prev, is_sso_signup: false })); 
        }

        return res.json();
    };

    const handleCurrencyChange = async (e) => {
        const newCurrency = e.target.value;
        try {
            await handleProfileUpdate({ currency: newCurrency });
            setProfileData(prev => ({ ...prev, currency: newCurrency }));
            setChangedField("Currency");
            setShowPopup(true);
            
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
            timeoutRef.current = setTimeout(() => {
                setShowPopup(false);
            }, 4000);
        } catch (error) {
            console.error('Error updating currency:', error);
        }
    };

    const handleTimezoneChange = async (e) => {
        const newTimezone = e.target.value;
        try {
            await handleProfileUpdate({ timezone: newTimezone });
            setProfileData(prev => ({ ...prev, timezone: newTimezone }));
            setChangedField("Timezone");
            setShowPopup(true);
            
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
            timeoutRef.current = setTimeout(() => {
                setShowPopup(false);
            }, 4000);
        } catch (error) {
            console.error('Error updating timezone:', error);
        }
    };

    // get settings data from backend
    const fetchSettingsData = async () => {
        const res = await fetch(`${API_HOST}/settings/`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });

        if (res.ok) {
            const data = await res.json();
            const newProfileData = {
                fullname: data?.fullname || ((data.firstname ? data.firstname : "") + (data.lastname ? (" " + data.lastname) : "")),
                email: data.email || "",
                companyname: data.companyname || "",
                companyaddress: data.companyaddress || "",
                currency: data.currency || "USD",
                timezone: data.timezone || "GMT+0",
                is_sso_signup: data.is_sso_signup,
                two_factor_enabled: data.two_factor_enabled
            };
            setProfileData(newProfileData);
            setDraftEmail(newProfileData.email);
            setDraftName(newProfileData.fullname);
            setDraftCompanyName(newProfileData.companyname);
            setDraftCompanyAddress(newProfileData.companyaddress);
            setFormData({street: data.street || "", city: data.city || "", state: data.state || "", postcode: data.postcode || ""});
        }
    }

    // Add security data fetching function
    const fetchSecurityData = async () => {
        try {
            const res = await fetch(`${API_HOST}/settings/activity`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                },
            });

            if (res.ok) {
                const data = await res.json();
                setActivityData(data);
            }
        } catch (error) {
            console.error('Error fetching security data:', error);
        }
    };

    const verifyPassword = async () => {            
        const input = document.querySelector('.verify_2fa input')
        const result = document.querySelector('.verify_2fa p')
        const password = input.value;

        try {
            const res = await fetch(`${API_HOST}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email: profileData.email, 
                    password 
                }),
            });               

            if(res.status == 200) {                
                setShow2faPopup(true)
                if (timeoutRef.current) clearTimeout(timeoutRef.current);
                timeoutRef.current = setTimeout(() => setShowPopup(false), 4000);
                result.style.display = "hidden"
                input.style.borderColor = "#2A2A2A" 
            } else {
                result.style.display = "block"
                input.style.borderColor = "#FF3F51" 
            }
        } catch (err) {
            console.error(`Error updating Two-Factor Authentication :`, err);
        }
    }
    

    // Add 2FA toggle handler
    const handlePreferenceToggle = async (field) => {
        let newValue
        let payload;
        newValue = !activityData.notify[field];
        payload = {
            notify: {
                [field]: newValue
            }
        };

        try {
            await fetch(`${API_HOST}/settings/preferences`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });
            
            setChangedField("Notification Preference");
            setActivityData((prev) => ({ ...prev,  notify: { ...prev.notify, [field]: newValue }}));
            setShowPopup(true);

            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            timeoutRef.current = setTimeout(() => setShowPopup(false), 4000);
        } catch (error) {
            console.error(`Error updating ${field}:`, error);
        }
    };

    const logout = () => {
        clearSessionCookies();
        window.location.reload();
    }

    const checkTyped = () => {
        const inputs = document.querySelectorAll(".setting_profile_fields input");

        const hasValue = Array.from(inputs).some((input) => input.value.trim() !== "");
        setShowsaveButton(hasValue);
    };

    useEffect(() => {
        fetchSettingsData();
        fetchSecurityData();
    }, [])

    const deleteAccount = async () => {
        try {
            let resp = await fetch(`${API_HOST}/user/delete_profile`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({})
            });
            
            if (resp.ok) {
                logout();
            }
        } catch (error) {
            console.error('Error deleting account:', error);
        }
    }

    const toggleSettingMenu = () => {
        const menu = document.querySelector(".settings_menu_wrap")
        menu.classList.toggle("show")
    }

    const showSavePopup = (title, value) => {
        setChangedField(title);
        setShowPopup(true);
        value = value == 'enable' ? true : false
        setProfileData((prev) => ({ ...prev,  two_factor_enabled: value}));
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => setShowPopup(false), 4000);
        setPasswordConfirm(false)
    }  

    return (
        <>
            <div className={`save_popup_wrap ${showPopup ? "show" : ""}`}>
                <div className="save_popup">
                    <div className="img_wrap">
                        <img src="/next_images/tick.svg"/>
                    </div>
                    <p>{changedField} Changed Successfully</p>
                    <div className="_loading">
                        <span></span>
                    </div>
                </div>
            </div>
            <div className="setting_wrap" onClick={(e) => e.stopPropagation()}>
                <div className="settings_popup">
                    <div className="settings_menu_bar">
                        <h1 className="settings_title">Settings</h1>
                        <div className="settings_title_mobile" ref={toggleRef} onClick={toggleSettingMenu}>
                            <h1>{settingsDropdown}</h1>
                            <img src="/next_images/arrow-square-up.svg"/>
                        </div>
                        <div className="settings_menu_wrap" ref={menuRef}>
                            <div id="account-tab" className="settings_tab selected" onClick={() => switchSettings("account")}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="21" height="20" viewBox="0 0 21 20" fill="none">
                                    <path d="M10.599 10.6458C10.5406 10.6375 10.4656 10.6375 10.399 10.6458C8.93229 10.5958 7.76562 9.39583 7.76562 7.92083C7.76562 6.4125 8.98229 5.1875 10.499 5.1875C12.0073 5.1875 13.2323 6.4125 13.2323 7.92083C13.224 9.39583 12.0656 10.5958 10.599 10.6458Z" stroke="#9E9E9E" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M16.1161 16.1547C14.6328 17.513 12.6661 18.338 10.4995 18.338C8.33281 18.338 6.36615 17.513 4.88281 16.1547C4.96615 15.3714 5.46615 14.6047 6.35781 14.0047C8.64115 12.488 12.3745 12.488 14.6411 14.0047C15.5328 14.6047 16.0328 15.3714 16.1161 16.1547Z" stroke="#9E9E9E" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M10.4974 18.3307C15.0998 18.3307 18.8307 14.5998 18.8307 9.9974C18.8307 5.39502 15.0998 1.66406 10.4974 1.66406C5.89502 1.66406 2.16406 5.39502 2.16406 9.9974C2.16406 14.5998 5.89502 18.3307 10.4974 18.3307Z" stroke="#9E9E9E" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                                Profile
                            </div>
                            <div id="general-tab" className="settings_tab" onClick={() => switchSettings("general")}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="21" height="20" viewBox="0 0 21 20" fill="none">
                                    <path d="M7.9974 18.3307H12.9974C17.1641 18.3307 18.8307 16.6641 18.8307 12.4974V7.4974C18.8307 3.33073 17.1641 1.66406 12.9974 1.66406H7.9974C3.83073 1.66406 2.16406 3.33073 2.16406 7.4974V12.4974C2.16406 16.6641 3.83073 18.3307 7.9974 18.3307Z" stroke="#9E9E9E" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M13.4766 15.4219V12.1719" stroke="#9E9E9E" strokeWidth="1.25" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M13.4766 6.21094V4.58594" stroke="#9E9E9E" strokeWidth="1.25" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M13.4714 10.5443C14.668 10.5443 15.638 9.57422 15.638 8.3776C15.638 7.18099 14.668 6.21094 13.4714 6.21094C12.2747 6.21094 11.3047 7.18099 11.3047 8.3776C11.3047 9.57422 12.2747 10.5443 13.4714 10.5443Z" stroke="#9E9E9E" strokeWidth="1.25" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M7.52344 15.4141V13.7891" stroke="#9E9E9E" strokeWidth="1.25" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M7.52344 7.83594V4.58594" stroke="#9E9E9E" strokeWidth="1.25" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M7.52604 13.7943C8.72266 13.7943 9.69271 12.8242 9.69271 11.6276C9.69271 10.431 8.72266 9.46094 7.52604 9.46094C6.32942 9.46094 5.35938 10.431 5.35938 11.6276C5.35938 12.8242 6.32942 13.7943 7.52604 13.7943Z" stroke="#9E9E9E" strokeWidth="1.25" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                                General
                            </div>
                            <div id="notification-tab" className="settings_tab" onClick={() => switchSettings("notification")}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="21" height="20" viewBox="0 0 21 20" fill="none">
                                    <path d="M10.5175 2.42188C7.75914 2.42188 5.51747 4.66354 5.51747 7.42188V9.83021C5.51747 10.3385 5.30081 11.1135 5.04247 11.5469L4.08414 13.1385C3.49247 14.1219 3.90081 15.2135 4.98414 15.5802C8.57581 16.7802 12.4508 16.7802 16.0425 15.5802C17.0508 15.2469 17.4925 14.0552 16.9425 13.1385L15.9841 11.5469C15.7341 11.1135 15.5175 10.3385 15.5175 9.83021V7.42188C15.5175 4.67188 13.2675 2.42188 10.5175 2.42188Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round"/>
                                    <path d="M12.0599 2.66719C11.8016 2.59219 11.5349 2.53385 11.2599 2.50052C10.4599 2.40052 9.69323 2.45885 8.97656 2.66719C9.21823 2.05052 9.81823 1.61719 10.5182 1.61719C11.2182 1.61719 11.8182 2.05052 12.0599 2.66719Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M13.0156 15.8828C13.0156 17.2578 11.8906 18.3828 10.5156 18.3828C9.83229 18.3828 9.19896 18.0995 8.74896 17.6495C8.29896 17.1995 8.01562 16.5661 8.01562 15.8828" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10"/>
                                </svg>
                                Notification
                            </div>
                            <div id="api-tab" className="settings_tab" onClick={() => switchSettings("api")}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20" fill="none">
                                    <path d="M16.4912 12.4406C14.7746 14.149 12.3162 14.674 10.1579 13.999L6.23289 17.9156C5.94955 18.2073 5.39122 18.3823 4.99122 18.324L3.17455 18.074C2.57455 17.9906 2.01622 17.424 1.92455 16.824L1.67455 15.0073C1.61622 14.6073 1.80789 14.049 2.08289 13.7656L5.99955 9.84896C5.33289 7.68229 5.84955 5.22396 7.56622 3.51563C10.0246 1.05729 14.0162 1.05729 16.4829 3.51563C18.9496 5.97396 18.9496 9.98229 16.4912 12.4406Z" stroke="#9E9E9E" strokeWidth="1.25" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M5.74219 14.5781L7.65885 16.4948" stroke="#9E9E9E" strokeWidth="1.25" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M12.0859 9.16406C12.7763 9.16406 13.3359 8.60442 13.3359 7.91406C13.3359 7.22371 12.7763 6.66406 12.0859 6.66406C11.3956 6.66406 10.8359 7.22371 10.8359 7.91406C10.8359 8.60442 11.3956 9.16406 12.0859 9.16406Z" stroke="#9E9E9E" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                                API & Keys  
                            </div>
                        </div>
                    </div>
                    <div className="settings_menu">
                        <div className="setting_profile settings_section" id="account" style={{display: 'flex'}}>
                            <h1 className="settings_title">Profile</h1>
                            <div className="setting_profile_fields">
                                <label>Full Name</label>
                                <div className="field_wrap">
                                    <div className="input_wrap" onClick={() => setEditInput(!editInput)}>
                                        <input className={`${editInput ? 'focused': ''}`} autoComplete="new-password" value={editInput ? draftName : profileData.fullname} readOnly={!editInput} onChange={(e) => setDraftName(e.target.value)}/>
                                        {!editInput && <img src="/next_images/edit.svg"/>}
                                    </div>
                                    {editInput &&
                                        <>
                                            <button onClick={(e) => saveChange("fullname")}>Save</button>
                                        </>
                                    }   
                                </div>
                            </div>
                            <div className="setting_profile_fields">
                                <label>Email Address</label>
                                <div className="field_wrap">
                                    <div className="input_wrap" onClick={() => setEditEmail(!editEmail)}>
                                        <input className={editEmail ? "focused" : ''} value={editEmail ? draftEmail : profileData.email} readOnly={!editEmail} onChange={(e) => setDraftEmail(e.target.value)}/>
                                        {!editEmail && <img src="/next_images/edit.svg"/>}
                                    </div>
                                    {editEmail &&
                                        <>
                                            <button onClick={(e) => saveChange("email")}>Update</button>
                                        </>
                                    }   
                                </div>
                            </div>
                            <div className={`setting_change_password ${changePassword ? 'edit':''}`}>
                                {changePassword ? 
                                    <>
                                        <h2>Change Password</h2>
                                        <div className="change_password_field">
                                            <div className="change_password_field_wrap">
                                                {!profileData.is_sso_signup && 
                                                    <>
                                                        <label>Current  Password</label>
                                                        <div>
                                                            <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}/>
                                                            <img/>
                                                        </div>
                                                    </>
                                                }
                                        </div>
                                            <div className="change_password_field_wrap">
                                                <label>{profileData.is_sso_signup ? 'Set' : 'New'} Password</label>
                                                <div>
                                                    <input type={hidePassword? 'password' : 'text'} name="new-password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}/>
                                                    <img src={hidePassword ? "/next_images/eye.svg" : "/next_images/hidden_eye.svg"} onClick={() => setHidePassword(!hidePassword)}/>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="button_wrap">
                                            <button onClick={() => setChangePassword(false)}>Cancel</button>
                                            <button onClick={(e) => saveChange("password")}>Save </button>
                                        </div>
                                    </>
                                    :
                                    <button className="change_button" onClick={() => setChangePassword(true)}><img src="/next_images/lock.svg"/>Change Password</button>
                                }
                            </div>
                            <div className="setting_2fa">
                                <div className="settings_switch">
                                    <h3>Two-Factor Authentication</h3>
                                    <div 
                                        className={`_switch ${profileData.two_factor_enabled ? 'on' : ''}`} 
                                        onClick={() => setPasswordConfirm(true)}
                                    >
                                        <span></span>
                                    </div>
                                </div>
                                <label>Two-Factor Authentication adds an extra layer of security to your Statement account. Each time you log in, after entering your username and password, you will be prompted to provide a second authentication code. This code can either be sent to you via email or generated through an authentication app such as Google Authenticator or Authy.</label>
                                {passwordConfirm && 
                                    <div className="verify_2fa">
                                        <div className="_label">
                                            <h4>Enter your password</h4>
                                            <span onClick={() => setHidePasswordVerify(!hidePasswordVerify)}><img src={hidePasswordVerify ? "/next_images/eye.svg" : "/next_images/hidden_eye.svg"}/>{hidePasswordVerify ? 'View' : 'Hide'}</span>
                                        </div>
                                        <input placeholder="Confirm Passowrd" type={hidePasswordVerify? 'password': 'text'}/>
                                        <p>Incorrect password. Please try again.</p>
                                        <div className="button_wrap">
                                            <button onClick={() => setPasswordConfirm(false)}>Cancel</button>
                                            <button onClick={verifyPassword}>Continue</button>
                                        </div>
                                    </div>
                                }    
                            </div>
                            <div className="account_settings">
                                <h1>Account Settings</h1>
                                <a onClick={() => setIsDeletingProfile(true)}>Delete Account</a>
                            </div>
                        </div>
                        <div className="settings_general settings_section" id="general">
                            <h1 className="settings_title">General</h1>
                            <div className="setting_profile_fields">
                                <div className="field_wrap">
                                    <div className="input_wrap" onClick={() => setEditCompanyName(true)}>
                                        <input className={editCompanyName ? 'focused' : ''} value={editCompanyName ? draftCompanyName : profileData.companyname} readOnly={!editCompanyName} onChange={(e) => setDraftCompanyName(e.target.value)} placeholder="Company Name"/>
                                        {!editCompanyName && <img src="/next_images/edit.svg"/>}
                                    </div>
                                    {editCompanyName &&
                                        <>
                                            <button onClick={(e) => saveChange("companyname")}>
                                                Save
                                            </button>
                                        </>
                                    }   
                                </div>
                            </div>
                            <form className="setting_profile_fields" onSubmit={(e) => e.preventDefault()}>
                                <label>Address</label>
                                <input 
                                    name="street"
                                    placeholder="Street name *" 
                                    value={formData.street}
                                    onChange={handleFormChange}
                                />
                                <input 
                                    name="city"
                                    placeholder="City *" 
                                    required 
                                    value={formData.city}
                                    onChange={handleFormChange}
                                />
                                <input 
                                    name="state"
                                    placeholder="State/ Province/ Region" 
                                    value={formData.state}
                                    onChange={handleFormChange}
                                />
                                <input 
                                    name="postcode"
                                    placeholder="Post Code *" 
                                    required 
                                    value={formData.postcode}
                                    onChange={handleFormChange}
                                />
                                {showSaveButton && 
                                    <div className="button_wrap">
                                        <button 
                                            type="button" 
                                            onClick={() => {
                                                setFormData({ street: "", city: "", state: "", postcode: "" });
                                                setShowsaveButton(false);
                                            }}
                                        >
                                            Cancel
                                        </button>
                                        <button 
                                            type="button" 
                                            onClick={() => saveChange("address")}
                                        >
                                            Save
                                        </button>
                                    </div>
                                }
                            </form>
                            <div className="setting_profile_fields">
                                <label>Currency</label>
                                <select value={profileData.currency} onChange={handleCurrencyChange}>
                                    {CURRENCIES.map(currency => (
                                        <option key={currency.value} value={currency.value}>{currency.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="setting_profile_fields">
                                <label>Timezone</label>
                                <select value={profileData.timezone} onChange={handleTimezoneChange}>
                                    {TIMEZONES.map(timezone => (
                                        <option key={timezone.value} value={timezone.value}>{timezone.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <ApiScreen/>
                        <div className="settings_notification settings_section" id="notification">
                            <h1 className="settings_title">Notifications</h1>
                            <h2 className="settings_subtitle">Financial Alerts</h2>
                            <div className="settings_switch">
                                <label>Get notified when key financial thresholds are crossed or anomalies are detected.</label>
                                <div className={`_switch ${(activityData.notify?.notifyFinancial == false) ? '' : 'on'}`} onClick={() => handlePreferenceToggle("notifyFinancial")}>
                                    <span></span>
                                </div>
                            </div>
                            <h2 className="settings_subtitle">Reports & Summaries</h2>
                            <div className="settings_switch">
                                <label>Get notified when scheduled reports or financial summaries are ready.</label>
                                <div className={`_switch ${activityData.notify?.notifyReports ? '' : 'on'}`} onClick={() => handlePreferenceToggle("notifyReports")}>
                                    <span></span>
                                </div>
                            </div>
                            <h2 className="settings_subtitle">Insights & Recommendations</h2>
                            <div className="settings_switch">
                                <label>Get notified when Statement generates new insights or recommendations.</label>
                                <div className={`_switch on ${(activityData.notify?.notifyInsights == false) ? '' : 'on'}`} onClick={() => handlePreferenceToggle("notifyInsights")}>
                                    <span></span>
                                </div>
                            </div>
                            <h2 className="settings_subtitle">Integrations</h2>
                            <div className="settings_switch">
                                <label>Get notified when a data sync succeeds, fails, or requires attention.</label>
                                <div className={`_switch ${(activityData.notify?.notifyIntegrations == false) ? '' : 'on'}`} onClick={() => handlePreferenceToggle("notifyIntegrations")}>
                                    <span></span>
                                </div>
                            </div>
                            <h2 className="settings_subtitle">Billing & Subscription</h2>
                            <div className="settings_switch">
                                <label>Get notified about invoices, payments, renewals, or billing issues.</label>
                                <div className={`_switch  ${(activityData.notify?.notifyBilling  == false) ? '' : 'on'}`} onClick={() => handlePreferenceToggle("notifyBilling")}>
                                    <span></span>
                                </div>
                            </div>
                            <h2 className="settings_subtitle">Account & Security</h2>
                            <div className="settings_switch">
                                <label>Get notified about important account activity and security-related events.</label>
                                <div className={`_switch ${(activityData.notify?.notifyAccount == false) ? '' : 'on'}`} onClick={() => handlePreferenceToggle("notifyAccount")}>
                                    <span></span>
                                </div>
                            </div>
                            <h2 className="settings_subtitle">Product Updates</h2>
                            <div className="settings_switch">
                                <label>Get notified about new features, improvements, and product announcements.</label>
                                <div className={`_switch ${(activityData.notify?.notifyProduct == false) ? '' : 'on'}`} onClick={() => handlePreferenceToggle("notifyProduct")}>
                                    <span></span>
                                </div>
                            </div>
                            <h2 className="settings_subtitle">Marketing & Communications</h2>
                            <div className="settings_switch">
                                <label>Get notified about newsletters, case studies, and occasional promotional updates.</label>
                                <div className={`_switch ${(activityData.notify?.notifyMarketing == false) ? '' : 'on'}`} onClick={() => handlePreferenceToggle("notifyMarketing")}>
                                    <span></span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <button className="close_button" onClick={onClose}><img src="/next_images/close.svg"/></button>
                </div>
                {isDeletingProfile &&
                    <div className="delete-popup-overlay">
                        <div className="delete-popup">
                            <h2>Delete Account</h2>
                            <p>Are you sure you want to delete your account? This action cannot be undone.</p>
                            <div className="popup-actions">
                                <button className="btn cancel" onClick={() => setIsDeletingProfile(false)}>Cancel</button>
                                <button className="btn delete" onClick={() => deleteAccount()}>Delete</button>
                            </div>
                        </div>
                    </div>}
            </div>

            {show2faPopup && <TwoFactorAuth closePopup={() => setShow2faPopup(false)} saveChange={(title,value) => showSavePopup(title,value)} twoFactorAuthValue={profileData.two_factor_enabled == true ? 'disable' : 'enable'}/>}
        </>
    )
}