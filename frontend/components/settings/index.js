'use client'
import { useRef, useState, useEffect } from "react"
import { toast } from "react-toastify";

import '@/style/component/settings.scss';

// utils
import { getSessionIdFromCookie } from "@/utils/cookie";
import { removeCookie } from "@/utils/cookie";

// context
import { useProjectContext } from "@/context/ProjectContext";
import { useSession } from "@/context/SessionContext";

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

    const { project: projectContext } = useProjectContext();
    const { user: activeUser } = useSession();
    const { project } = projectContext;

    const userPlanSlug = activeUser?.subscription?.plan_slug || "free";

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
    const [apiKeys, setAPIKeys] = useState([])
    const [usageData, setUsageData] = useState(false)
    const [plans, setPlans] = useState([])
    const [showAddApiKey, setShowAddApiKey] = useState(false)
    const [newApiKeyName, setNewApiKeyName] = useState("")
    const [changePassword, setChangePassword] = useState(false)
    const [showSaveButton, setShowsaveButton] = useState(false)
    const [draftEmail, setDraftEmail] = useState("");
    const [hidePassword, setHidePassword] = useState(true);
    const [isDeletingProfile, setIsDeletingProfile] = useState(false);
    const [activityData, setActivityData] = useState({
        currentSessions: [],
        twoFactorEnabled: false,
        notifyResponses: false,
        notifyTaskUpdate: false,
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
    const sessionId = getSessionIdFromCookie();


    const timeoutRef = useRef(null);

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
                console.log("draftCompanyName: ",draftCompanyName)
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

    const switchSettings = (id, e) => {
        const selected = document.querySelectorAll(".settings_menu_wrap")
        selected.forEach((tab) => tab.classList.remove("selected"))
        e.target.classList.add("selected");

        const sections = document.querySelectorAll(".settings_section")
        sections.forEach(section => section.style.display = "none")

        document.querySelector(`#${id}`).style.display = "block"
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
        const res = await fetch(`${API_HOST}/settings`, {
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
                timezone: data.timezone || "GMT+0"
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

    // Add 2FA toggle handler
    const handlePreferenceToggle = async (field) => {
        const newValue = !activityData[field];
        try {
            await fetch(`${API_HOST}/settings/preferences`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ [field]: newValue }),
            });

            setActivityData((prev) => ({ ...prev, [field]: newValue }));
            if (field == "twoFactorEnabled") {
                setChangedField("2FA Settings");
            } else {
                setChangedField("Notification Preference");
            }
            setShowPopup(true);

            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            timeoutRef.current = setTimeout(() => setShowPopup(false), 4000);
        } catch (error) {
            console.error(`Error updating ${field}:`, error);
        }
    };

    const logout = () => {
        removeCookie("access_token")
        window.location.reload();
    }

    const checkTyped = () => {
        const inputs = document.querySelectorAll(".setting_profile_fields input");

        const hasValue = Array.from(inputs).some((input) => input.value.trim() !== "");
        setShowsaveButton(hasValue);
    };

    const handleClickOutside = (event) => {
        const isClickInsideInput = event.target.tagName === 'INPUT';
        const isClickInsideButton = event.target.tagName === 'BUTTON';

        if (!isClickInsideInput && !isClickInsideButton) {
            // Reset all edit states and draft values to original values
            if (editInput) {
                setDraftName(profileData.fullname);
                setEditInput(false);
            }
            if (editEmail) {
                setDraftEmail(profileData.email);
                setEditEmail(false);
            }
            if (editCompanyName) {
                setDraftCompanyName(profileData.companyname);
                setEditCompanyName(false);
            }
            if (editCompanyAddress) {
                setDraftCompanyAddress(profileData.companyaddress);
                setEditCompanyAddress(false);
            }
        }
    };

    useEffect(() => {
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [editInput, editEmail, editCompanyName, editCompanyAddress, changePassword, profileData]);

    useEffect(() => {
        fetchSettingsData();
        fetchSecurityData();
        loadPlans();
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

    useEffect(() => {
        loadProjectAPIKeys();
        loadUsageStats();
    }, [project])

    const loadProjectAPIKeys = async () => {
        if (!project || !project._id) return;
        const res = await fetch(`${API_HOST}/user/project/api_key?projectId=${project._id}`, {
            method: "GET"
        });

        if (res.ok) {
            let data = await res.json();
            let { keys } = data;
            setAPIKeys(keys); 
        }
    }

    const removeAPIKey = async (projectId, apiKeyId) => {
        const res = await fetch(`${API_HOST}/user/project/api_key`, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ projectId, apiKeyId }),
        });
        if (res.ok) {
            loadProjectAPIKeys();
        }
    }
    
    const createAPIKey = async () => {
        if (!project || !project._id) return;
        const res = await fetch(`${API_HOST}/user/project/api_key`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ projectId: project._id, name: newApiKeyName }),
        });
        if (res.ok) {
            setShowAddApiKey(false);
            setNewApiKeyName("");
            loadProjectAPIKeys();
        }
    }

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        toast.success("Copied to clipboard!", {
            position: "top-right",
            autoClose: 3000,
            hideProgressBar: false,
            closeOnClick: true,
            pauseOnHover: true,
            draggable: true,
            progress: undefined,
            theme: "dark",
        });
    }

    const loadUsageStats = async () => {
        if (!project || !project._id) return;
        const res = await fetch(`${API_HOST}/settings/usage?projectId=${project._id}`, {
            method: "GET"
        });

        if (res.ok) {
            let data = await res.json();
            let { usage } = data;
            setUsageData(usage); 
        }
    }

    const loadPlans = async () => {
        if (!project || !project._id) return;
        const res = await fetch(`${API_HOST}/settings/plans`, {
            method: "GET"
        });

        if (res.ok) {
            let data = await res.json();
            let { plans } = data;
            setPlans(plans)
        }
    }

    let currentPlan = plans.find(plan => plan.slug === userPlanSlug);

    return (
        <div className="setting_wrap" onClick={(e) => e.stopPropagation()}>
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
            <div className="settings_popup">
                <div className="settings_menu_bar">
                    <h1 className="settings_title">Settings</h1>
                    <div className="settings_menu_wrap selected" onClick={(e) => switchSettings("account",e)}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="21" height="20" viewBox="0 0 21 20" fill="none">
                            <path d="M10.599 10.6458C10.5406 10.6375 10.4656 10.6375 10.399 10.6458C8.93229 10.5958 7.76562 9.39583 7.76562 7.92083C7.76562 6.4125 8.98229 5.1875 10.499 5.1875C12.0073 5.1875 13.2323 6.4125 13.2323 7.92083C13.224 9.39583 12.0656 10.5958 10.599 10.6458Z" stroke="#9E9E9E" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M16.1161 16.1547C14.6328 17.513 12.6661 18.338 10.4995 18.338C8.33281 18.338 6.36615 17.513 4.88281 16.1547C4.96615 15.3714 5.46615 14.6047 6.35781 14.0047C8.64115 12.488 12.3745 12.488 14.6411 14.0047C15.5328 14.6047 16.0328 15.3714 16.1161 16.1547Z" stroke="#9E9E9E" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M10.4974 18.3307C15.0998 18.3307 18.8307 14.5998 18.8307 9.9974C18.8307 5.39502 15.0998 1.66406 10.4974 1.66406C5.89502 1.66406 2.16406 5.39502 2.16406 9.9974C2.16406 14.5998 5.89502 18.3307 10.4974 18.3307Z" stroke="#9E9E9E" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        Profile
                    </div>
                    <div className="settings_menu_wrap" onClick={(e) => switchSettings("general",e)}>
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
                    <div className="settings_menu_wrap" onClick={(e) => switchSettings("plan",e)}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="19" height="16" viewBox="0 0 19 16" fill="none">
                            <path d="M11.9974 12.1693H8.66406M6.16406 12.1693H4.4974M1.17327 6.33594C1.16406 6.81679 1.16406 7.36633 1.16406 8.0026C1.16406 10.3362 1.16406 11.5029 1.6182 12.3942C2.01767 13.1782 2.65509 13.8157 3.4391 14.2151C4.3304 14.6693 5.49718 14.6693 7.83073 14.6693H11.1641C13.4976 14.6693 14.6644 14.6693 15.5557 14.2151C16.3397 13.8157 16.9771 13.1782 17.3766 12.3942C17.8307 11.5029 17.8307 10.3362 17.8307 8.0026C17.8307 7.36633 17.8307 6.81679 17.8215 6.33594M1.17327 6.33594C1.19783 5.05325 1.28789 4.25925 1.6182 3.61098C2.01767 2.82697 2.65509 2.18955 3.4391 1.79008C4.3304 1.33594 5.49718 1.33594 7.83073 1.33594H11.1641C13.4976 1.33594 14.6644 1.33594 15.5557 1.79008C16.3397 2.18955 16.9771 2.82697 17.3766 3.61098C17.7069 4.25925 17.797 5.05325 17.8215 6.33594M1.17327 6.33594H17.8215" stroke="#9E9E9E" strokeWidth="1.4" strokeLinecap="round"/>
                        </svg>
                        Plan & Billing  
                    </div>
                    <div className="settings_menu_wrap" onClick={(e) => switchSettings("api",e)}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                            <path d="M6 10V8C6 4.69 7 2 12 2C17 2 18 4.69 18 8V10" stroke="#9D9D9D" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M12 18.5C13.3807 18.5 14.5 17.3807 14.5 16C14.5 14.6193 13.3807 13.5 12 13.5C10.6193 13.5 9.5 14.6193 9.5 16C9.5 17.3807 10.6193 18.5 12 18.5Z" stroke="#9D9D9D" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M17 22H7C3 22 2 21 2 17V15C2 11 3 10 7 10H17C21 10 22 11 22 15V17C22 21 21 22 17 22Z" stroke="#9D9D9D" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        API & Keys  
                    </div>
                    <div className="settings_menu_wrap" onClick={(e) => switchSettings("notification",e)}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="21" height="20" viewBox="0 0 21 20" fill="none">
                            <path d="M10.5175 2.42188C7.75914 2.42188 5.51747 4.66354 5.51747 7.42188V9.83021C5.51747 10.3385 5.30081 11.1135 5.04247 11.5469L4.08414 13.1385C3.49247 14.1219 3.90081 15.2135 4.98414 15.5802C8.57581 16.7802 12.4508 16.7802 16.0425 15.5802C17.0508 15.2469 17.4925 14.0552 16.9425 13.1385L15.9841 11.5469C15.7341 11.1135 15.5175 10.3385 15.5175 9.83021V7.42188C15.5175 4.67188 13.2675 2.42188 10.5175 2.42188Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round"/>
                            <path d="M12.0599 2.66719C11.8016 2.59219 11.5349 2.53385 11.2599 2.50052C10.4599 2.40052 9.69323 2.45885 8.97656 2.66719C9.21823 2.05052 9.81823 1.61719 10.5182 1.61719C11.2182 1.61719 11.8182 2.05052 12.0599 2.66719Z" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M13.0156 15.8828C13.0156 17.2578 11.8906 18.3828 10.5156 18.3828C9.83229 18.3828 9.19896 18.0995 8.74896 17.6495C8.29896 17.1995 8.01562 16.5661 8.01562 15.8828" stroke="#9D9D9D" strokeWidth="1.4" strokeMiterlimit="10"/>
                        </svg>
                        Notification
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
                                            <label>Current  Password</label>
                                            <div>
                                                <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}/>
                                                <img/>
                                            </div>
                                        </div>
                                        <div className="change_password_field_wrap">
                                            <label>New Password</label>
                                            <div>
                                                <input type={hidePassword? 'password' : 'text'} value={newPassword} onChange={(e) => setNewPassword(e.target.value)}/>
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
                                    className={`_switch ${activityData.twoFactorEnabled ? 'on' : ''}`} 
                                    onClick={() => handlePreferenceToggle("twoFactorEnabled")}
                                >
                                    <span></span>
                                </div>
                            </div>
                            <label>Two-Factor Authentication adds an extra layer of security to your Statement account. Each time you log in, after entering your username and password, you will be prompted to provide a second authentication code. This code can either be sent to you via email or generated through an authentication app such as Google Authenticator or Authy.</label>
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
                    <div className="setting_bill settings_section" id="plan">
                        <h1 className="settings_title">Plan & Billing</h1>
                        <div className="usage_stats">
                            <h2 className="settings_subtitle">Usage Statistics</h2>
                            <div className="usage_items">
                                <div className="usage_item">
                                    <h3>Allowed Credits</h3>
                                    <p>{usageData.credits_allowed || 0}</p>
                                </div>
                                <div className="usage_item">
                                    <h3>Credits Used</h3>
                                    <p title={usageData.credits_used}>
                                        {usageData.credits_used
                                        ? Math.ceil(usageData.credits_used)
                                        : 0}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <h2 className="settings_subtitle">Current Plan</h2>
                        <div className="current_plan">{currentPlan?.name}</div>
                        <div className="setting_plans">
                            {plans && plans.map((plan, index) =>
                                <div className={`plan_tile ${currentPlan && currentPlan.slug === plan.slug ? 'current' : ''}`} key={index}>
                                    <h3>{plan.name}</h3>
                                    <p className="plan_price">${plan.price_monthly} <span>/ month</span></p>
                                    <p className="plan_description">{plan.description}</p>
                                    <ul>
                                        {plan.features.map((feature, fIndex) => 
                                            <li key={fIndex}>
                                                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 11 11" fill="none">
                                                    <path d="M8.96145 2.6875L4.03043 7.61847L1.78906 5.37713" stroke="#48C884" strokeWidth="1.34482" strokeLinecap="round" strokeLinejoin="round"/>
                                                </svg>
                                                <div className="text">{feature}</div>
                                            </li>
                                        )}
                                    </ul>
                                    <button 
                                        className="plan_btn"
                                        disabled={currentPlan && currentPlan.slug === plan.slug} 
                                        onClick={() => {}}
                                    >
                                        {currentPlan && currentPlan.slug === plan.slug ? "Current Plan" : "Upgrade"}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="setting_api_key settings_section" id="api">
                        <h1 className="settings_title">API & Keys</h1>
                        <button className="create_new-key-btn" onClick={() => setShowAddApiKey(true)}>Create API Key</button>
                        <table className="api_keys_table">
                            <thead>
                                <tr>
                                    <th className="name">Name</th>
                                    <th className="api-key">API Key</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {apiKeys && apiKeys.map((key, index) => (
                                    <tr key={index}>
                                        <td className="name">{key.name}</td>
                                        <td className="api-key">
                                            <div className="key_value">{key.api_key}</div>
                                            <img src="/next_images/copy.svg" className="copy-btn" onClick={() => copyToClipboard(key.api_key)}/>
                                        </td>
                                        <td>
                                            <button onClick={() => removeAPIKey(project._id, key._id)}>Delete</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {showAddApiKey && <div className="settings_add_apikey-popup">
                            <div className="settings_add_apikey-content">
                                <h2>Create New API Key</h2>
                                <input 
                                    type="text" 
                                    placeholder="Enter API Key Name" 
                                    value={newApiKeyName} 
                                    onChange={(e) => setNewApiKeyName(e.target.value)}
                                    maxLength="40"
                                />
                                <div className="button_wrap">
                                    <button onClick={() => setShowAddApiKey(false)}>Cancel</button>
                                    <button onClick={createAPIKey}>Create</button>
                                </div>
                            </div>
                        </div>}
                    </div>
                    <div className="settings_notification settings_section" id="notification">
                        <h1 className="settings_title">Notifications</h1>
                        <h2 className="settings_subtitle">Responses</h2>
                        <div className="settings_switch">
                            <label>Get notified when Statement responds to requests that take time.</label>
                            <div className={`_switch ${activityData.notifyResponses ? 'on' : ''}`} onClick={() => handlePreferenceToggle("notifyResponses")}>
                                <span></span>
                            </div>
                        </div>
                        <h2 className="settings_subtitle">Task Update</h2>
                        <div className="settings_switch">
                            <label>Get notified when Statement responds to requests that take time.</label>
                            <div className={`_switch ${activityData.notifyTaskUpdate ? 'on' : ''}`} onClick={() => handlePreferenceToggle("notifyTaskUpdate")}>
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
    )
}