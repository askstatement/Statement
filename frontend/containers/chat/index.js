"use client";
import { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSearchParams } from 'next/navigation';

// utils
import NewsInsights from '@/components/chat/newsInsights';
import ChatBot from '@/components/chat/chatBot';
import History from '@/components/chat/history';

// context
import { useProjectContext } from "@/context/ProjectContext";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function Chats() {

    const searchParams = useSearchParams();
    const currentTab = searchParams.get('tab') || 'insights';
    const convIdQuery = searchParams.get('convId');
    const emailStatus = searchParams.get('everify');
    const qbRealmId = searchParams.get('realmId');

    const serviceMap = new Map([
        ['xero', { statusKey: 'xeroStatus', codeVar: 'xeroCode' }],
        ['quickbooks', { statusKey: 'qbStatus', codeVar: 'qbCode' }],
        ['stripe', { statusKey: 'stripe_status', codeVar: 'stripeCode' }]
    ]);

    function assignAuthCode(searchParams, serviceMap) {
        const authCode = searchParams.get('code');
        const result = { stripeCode: false, xeroCode: false, qbCode: false };

        if (!authCode) return result;

        for (const [service, config] of serviceMap) {
            if (searchParams.get(config.statusKey) === 'connected') {
                result[config.codeVar] = authCode;
                break; // Process in priority order
            }
        }

        return result;
    }

    const { stripeCode, xeroCode, qbCode } = assignAuthCode(searchParams, serviceMap);

    const { updateProjectContext } = useProjectContext();

    useEffect(() => {
        const fetchProjectDetails = async () => {
            let createProject = false;
            try {
                const res = await fetch(`${API_HOST}/user/projects`, {
                    method: "GET",
                    headers: {
                    "Content-Type": "application/json",
                    },
                });
        
                if (res.ok) {
                    const data = await res.json();
                    if (data.projects.length > 0) {
                        let project = null
                        // find the project matching the convId
                        if (!convIdQuery)
                            project = data.projects.find(p => p.chats.some(chat => chat._id === convIdQuery));
                        updateProjectContext({
                            project: data.projects.length > 0 ? data.projects[0] : null, 
                            convIdQuery, all: data.projects || [] 
                        })
                    } else createProject = true
                } else createProject = true
            } catch (error) {
                createProject = true
                console.error("Error fetching project details:", error);
            }
        };
        fetchProjectDetails();
    }, [convIdQuery]);

    useEffect(() => {
        const showVerificationPopup = async () => {
            try {
                if (emailStatus === "success") {
                    toast.success("Email verified successfully!", {
                        position: "top-right",
                        autoClose: 5000,
                        hideProgressBar: false,
                        closeOnClick: false,
                        pauseOnHover: true,
                        draggable: true,
                        progress: undefined,
                        theme: "dark",
                    });
                } else if (emailStatus === "failed") {
                    toast.error("Email verification failed or the link has expired. Please try again.", {
                        position: "top-right",
                        autoClose: 5000,
                        hideProgressBar: false,
                        closeOnClick: false,
                        pauseOnHover: true,
                        draggable: true,
                        progress: undefined,
                        theme: "dark",
                    });
                }
            } catch (error) {
                router.push('/login?everify=failed')
            }
        };

        showVerificationPopup();
    }, [emailStatus]);

    return (
        <div className={`chat_layout_container`}>
            {currentTab == 'insights' && <NewsInsights stripeCode={stripeCode}/>}
            {currentTab == 'chat' && <ChatBot stripeCode={stripeCode} xeroCode={xeroCode} qbCode={qbCode} qbRealmId={qbRealmId} />}
            {currentTab == 'history' && <History/>}
        </div>
    )
}