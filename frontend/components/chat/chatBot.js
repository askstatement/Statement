"use client"
import "@/style/component/chatbot.scss";
import React, { useEffect, useState, useRef, useMemo } from "react";
import { createRoot } from "react-dom/client";
import { marked } from 'marked';
import { useRouter, useSearchParams } from 'next/navigation';

// components
import AddConnection from "@/components/chat/addConnection"; //imports the wrapper

// context
import { useProjectContext } from "@/context/ProjectContext";
import { useWebSocket } from "@/context/WebSocketContext";
import { toast } from "react-toastify";

// json
import suggestedQuestion from "@/components/chat/suggestionQuestion.json"

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function ChatBot (props) {

    const { stripeCode, xeroCode, qbCode, zohoCode, qbRealmId } = props;

    const router = useRouter();
    const searchParams = useSearchParams();
    const convIdQuery = searchParams.get('convId');
    let showConnect = searchParams.get('connect');
    showConnect = showConnect === "true"

    const { project } = useProjectContext();
    const { syncProgress } = useWebSocket();

    const loadingRef = useRef(null);
    const chatContainerRef = useRef(null);
    const sendButtonRef = useRef(null);
    const inputRef = useRef(null);
    const uploadIconRef = useRef(null);
    const attachFileRef = useRef(null);

    const [loading, setLoading] = useState({text: "One moment, compiling your answer…", isLoading: false})
    const [currentBotDiv, setCurrentBotDiv] = useState(null);
    const [isChatting, setIsChatting] = useState(false);
    const [convId, setConvId] = useState(convIdQuery);
    const [history, setChatHistory] = useState([]);
    const [chatError, setChatError] = useState(null);
    const [dataSources, setDataSources] = useState([])
    const [suggestedData, setSuggestedData] = useState([])
    const [activeTab, setActiveTab] = useState([])
    const [availableAgents, setAvailableAgents] = useState([])
    const [loadingIndex, setLoadingIndex] = useState(0);
    const [showAddConnection, setShowAddConnection] = useState(stripeCode || xeroCode || qbCode || zohoCode || showConnect ? true : false);
    const [showAgentSuggestions, setShowAgentSuggestions] = useState(false);
    const [filteredAgents, setFilteredAgents] = useState([]);
    const [mentionQuery, setMentionQuery] = useState('');
    const [mentionStartIndex, setMentionStartIndex] = useState(-1);
    const [selectedAgents, setSelectedAgents] = useState([])

    const loadingMessage = [
        "Gathering the numbers…",
        "Running the analysis…",
        "Finishing with fine details",
    ];

    const projectId = project?.project?._id
        ? project?.project?._id
        : null;

    const allProjects = project?.all ? project?.all : []

    const activeProject = project?.project ? project?.project : null;

    const plaidConnAccounts = activeProject
        ? activeProject?.plaid_account_details || []
        : null;

    useEffect(() => {
        if (convId) fetchHistory();
    }, []);

    useEffect(() => {
        if (!Array.isArray(dataSources) || dataSources.length === 0) return;

        if (dataSources.includes("stripe")) {
            setSuggestedData("stripe");
        } else if (dataSources.includes("paypal")) {
            setSuggestedData("paypal");
        } else {
            setSuggestedData("commonQuestions");
        }
    }, [dataSources]);
    
    useEffect(() => {
        if (projectId) loadAvailableAgents();
    }, [projectId]);

    useEffect(() => {
        loadProjectDataSources(project?.project || {});
    }, [project, showConnect]);

    useEffect(() => {
        setChatError(false);
        const input = inputRef.current;
        const sendButton = sendButtonRef.current;

        const handleKeyDown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendButton?.click();
            }
        };

        input.addEventListener('keydown', handleKeyDown);

        return () => {
            input.removeEventListener('keydown', handleKeyDown);
        };
    }, [convId]);
    
    useEffect(() => {
        if (!suggestedQuestion?.[suggestedData]) return;

        const tabs = document.querySelectorAll(".chat_suggested_tab span");

        tabs.forEach(tab => {
            if (tab.classList.contains("active")) {
                const active = suggestedQuestion[suggestedData].find(
                    q => q.title === tab.textContent
                );
                setActiveTab(active);
            }
        });

        const handleClick = (e) => {
            tabs.forEach(tab => tab.classList.remove("active"));
            e.target.classList.add("active");

            const clickedTab = suggestedQuestion[suggestedData].find(
                q => q.title === e.target.textContent
            );
            setActiveTab(clickedTab);
        };

        tabs.forEach(tab => tab.addEventListener("click", handleClick));

        return () => {
            tabs.forEach(tab => tab.removeEventListener("click", handleClick));
        };
    }, [suggestedData]);

    const randomQuestions = useMemo(() => {
        return activeTab?.questions
            ?.slice()
            .sort(() => Math.random() - 0.5)
            .slice(0, 5);
    }, [activeTab]);
        
    const activeSync = useMemo(() => {
        if (!syncProgress) return null;
        // Find the first service that is 'in-progress'
        const inProgressSync = Object.values(syncProgress).find(p => p.status === 'in-progress');

        if (!inProgressSync) return null;

        let current_step = 0;
        let total_steps = 1;

        if (inProgressSync.progress && typeof inProgressSync.progress === 'string') {
            const parts = inProgressSync.progress.split('/');
            if (parts.length === 2) {
                current_step = parseInt(parts[0], 10) || 0;
                total_steps = parseInt(parts[1], 10) || 1;
            }
        }

        return {
            ...inProgressSync,
            current_step,
            total_steps,
        };
    }, [syncProgress]);


    useEffect(() => {
        const sb = attachFileRef.current;
        const icon = uploadIconRef.current;

        const handleIconClick = () => sb.click();
        const handleFileChange = () => uploadFile(sb.files[0]);

        icon.addEventListener('click', handleIconClick);
        sb.addEventListener('change', handleFileChange);

        const observeCopyButton = () => {
            const copies = document.querySelectorAll(".chat-action.copy");
            if (!copies.length) return;

            const cleanups = [];

            copies.forEach((copy) => {
                const span = copy.querySelector("span");
                
                const handleCopyClick = () => {
                    copy.classList.add("copied");
                    span.textContent = "Copied";
                    setTimeout(() => {
                        copy.classList.remove("copied");
                        span.textContent = "Copy";
                    }, 1200);
                };

                copy.addEventListener("click", handleCopyClick);
                cleanups.push(() =>
                    copy.removeEventListener("click", handleCopyClick)
                );
            });

            return () => cleanups.forEach((fn) => fn());
        };

        let cleanupCopy = observeCopyButton();

        const observer = new MutationObserver(() => {
            cleanupCopy?.(); 
            cleanupCopy = observeCopyButton();
        });

        const chatContainer = document.querySelector('.chatbot_container')
        
        observer.observe(chatContainer, {
            childList: true,
            subtree: true,
        });

        return () => {
            icon.removeEventListener('click', handleIconClick);
            sb.removeEventListener('change', handleFileChange);
            window.chatSocket?.close();
        };
    }, [])

    useEffect(() => {
        if (!loading?.isLoading) return setLoadingIndex(0); // reset to first message;
        const interval = setInterval(() => {
            setLoadingIndex((prev) => {
                let nextIndex = prev + 1
                if (nextIndex >= loadingMessage.length) nextIndex = nextIndex - 1;
                return nextIndex;
            });
        }, 8000);

        return () => clearInterval(interval); 
    }, [loading]);

    const fetchHistory = async () => {
        if (!convId) return;
        // do nothing if the websocket is already open
        if (window.chatSocket !== null && window.chatSocket) return
        // clear previous chat messages
        chatContainerRef.current.innerHTML = '';

        if (history.length > 0) {
            setLoading({...loading, isLoading: true});
            loadingRef.current ? loadingRef.current.textContent = "Loading chat history…" : null;
        }

        const res = await fetch(`${API_HOST}/user/history?convoId=${convId}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });

        if (res.ok) {
            const data = await res.json();
            setChatHistory(data.history);
            if (data.history && data.history.length > 0) {
                setIsChatting(true);
                data.history.forEach(item => {
                    if (item.type === 'prompt') {
                        appendMessage(`<div class="chat-bubble user-bubble">${item.content}</div>`, 'user-message');
                    } else if (item.type === 'file_upload') {
                        appendMessage(`<div class="chat-bubble user-bubble file-upload-bubble">File uploaded: ${item.content}</div>`, 'user-message');
                    } else if (item.type === 'response') {
                        const { agent_responses = [] } = item || {};
                        if (agent_responses && agent_responses.length > 0) {
                            for (const agent of agent_responses) {
                                const { response_json = {} } = agent;
                                const { graph_data, follow_up = "", final_answer = "" } = response_json;
                                appendBotMessage({
                                    chunk: `${final_answer}${follow_up ? '\n\n' + follow_up : ''}`,
                                    graph_data: graph_data,
                                    speed: 20,
                                    enableTypingAnimation: false,
                                    promptId: item._id,
                                    reaction: item.reaction,
                                });
                            }
                        } else {
                            appendBotMessage({
                              chunk: `${item.content}${item.followup ? "\n\n" + item.followup : ""}`,
                              graph_data: item.graph_data,
                              speed: 20,
                              enableTypingAnimation: false,
                              promptId: item._id,
                              reaction: item.reaction,
                            });
                        }
                    }
                    setTimeout(() => {
                        const myDiv = document.getElementById("chatstreams");
                        myDiv.scrollTo({
                            top: myDiv.scrollHeight,
                            behavior: "smooth"
                        });
                    }, 500);
                });
            } else {
                console.warn("No chat history found");
            }
        } else {
            console.error("Failed to fetch history");
        }
        setLoading({...loading, isLoading: false});
    };

    useEffect(() => {
        const handleClick = (event) => {
            const copyButton = event.target.closest('.chat-action.copy');
            if (!copyButton) return;

            const chatBubble = copyButton.closest('.chat-bubble');
            if (!chatBubble) return;

            const botResponse = chatBubble.querySelector('.bot-response');
            if (!botResponse) return;

            const textToCopy = botResponse.textContent.trim();
            navigator.clipboard.writeText(textToCopy)
                .catch((err) => {
                    console.error('Failed to copy:', err);
                });
        };

        document.addEventListener('click', handleClick);
        return () => {
            document.removeEventListener('click', handleClick);
        };
    }, []);

    const appendMessage = (html, className = '') => {
        const wrapper = document.createElement('div');
        wrapper.className = `chat-message ${className}`;
        wrapper.innerHTML = html;
        chatContainerRef.current.appendChild(wrapper);
        chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        return wrapper;
    };

    const handleInput = (e) => {
        const el = e.target;
        const parentNode = el.parentNode;

        el.style.height = "21px"; 
        el.style.height = el.scrollHeight + "px"; 

        const value = el.value;
        const cursorPos = el.selectionStart;
        
        // Check for @ mention
        const textBeforeCursor = value.substring(0, cursorPos);
        const lastAtIndex = textBeforeCursor.lastIndexOf('@');
        
        if (lastAtIndex !== -1) {
            // Check if @ is followed by a space or at the end of text (new mention)
            const afterAt = textBeforeCursor.substring(lastAtIndex + 1);
            
            // If there's no space in the substring after @, it's a valid mention query
            if (!afterAt.includes(' ')) {
                const query = afterAt ? afterAt.toLowerCase() : "";
                setMentionQuery(query);
                setMentionStartIndex(lastAtIndex);
                
                // Filter agents based on query
                const filtered = availableAgents.filter(agent => 
                    agent.agent_name.toLowerCase().includes(query) ||
                    (agent.description && agent.description.toLowerCase().includes(query))
                );
                
                setFilteredAgents(filtered);
                setShowAgentSuggestions(filtered.length > 0);
            } else {
                setShowAgentSuggestions(false);
            }
        } else {
            setShowAgentSuggestions(false);
        }

        const trimmedValue = value.trim();

        if (trimmedValue) {
            parentNode.classList.add("typed");
            sendButtonRef.current.disabled = false;
        } else {
            parentNode.classList.remove("typed");
            sendButtonRef.current.disabled = true;
        }
    };
    
    useEffect(() => {
        const handleClick = (event) => {
            const thumbsUp = event.target.closest('.chat-action.thumbs-up');
            const thumbsDown = event.target.closest('.chat-action.thumbs-down');
            const bookMark = event.target.closest('.chat-action.bookmark');

            if (thumbsUp || thumbsDown) {
                const chatBubble = (thumbsUp || thumbsDown).closest('.chat-bubble');
                const promptId = chatBubble?.getAttribute('data-prompt-id') || null;
                const reaction = thumbsUp ? 'liked' : 'disliked';
                chatInteraction(reaction, promptId);

                chatBubble.querySelectorAll(".chat-action").forEach((e) => e.classList.remove('active'))
                event.target.closest('.chat-action').classList.add('active')
            }

        };

        document.addEventListener('click', handleClick);
        return () => document.removeEventListener('click', handleClick);
    }, []);

    const chatInteraction = async (interaction, promptId) => {     
        const res = await fetch(`${API_HOST}/user/record_reactions?promptId=${promptId}&reaction=${interaction}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });
    }


    const appendBotMessage = async ({
        chunk = "",
        graph_data = {},
        speed = 20, 
        enableTypingAnimation = false, 
        promptId = null, 
        reaction,
    }) => {
        if (!chunk) return;
        let botDiv = currentBotDiv;

        const wrapper = appendMessage(`
            <div class="chat-bubble bot-bubble" data-prompt-id="${promptId}">
                <div class="chart-wrapper"></div>
                <div class="bot-response"></div>
                <div class="chat-actions">
                    <button class="chat-action copy"><img src="/next_images/copy.svg" alt="Copy"/><span>Copy</span></button>
                    <button class="chat-action thumbs-up ${reaction == 'liked'? 'active': ''}"><img src="/next_images/like.svg" alt="Like"/></button>
                    <button class="chat-action thumbs-down ${reaction == 'disliked'? 'active': ''}"><img src="/next_images/dislike.svg" alt="Dislike"/></button>
                </div>
            </div>`, 'bot-message');

        botDiv = wrapper.querySelector('.bot-response');
        const chartWrapper = wrapper.querySelector('.chart-wrapper');
        const bubble = wrapper.querySelector('.chat-bubble');

        if (chunk.length > 1000) {
            enableTypingAnimation = false; // disable typing animation for long texts
            speed = 0;
        }

        if (graph_data && Object.keys(graph_data).length > 0) {
            try {
                const parsed = typeof graph_data === "string" ? JSON.parse(graph_data) : graph_data;
                const { value_map: graphData, title, type } = parsed;
                const currency_symbol = parsed.currency_symbol || parsed["currency-symbol"] || "";

                const xValues = Object.keys(graphData);
                const yValues = Object.values(graphData);

                const chartContainer = document.createElement("div");
                chartContainer.className = "chart-container";
                chartWrapper.appendChild(chartContainer);

                const chartProps = {
                  data: yValues || [],
                  xLabels: xValues || [],
                  title: title || "",
                  currency: currency_symbol || "",
                };

                console.debug("Rendering chart with props:", parsed);
                const root = createRoot(chartContainer);
                if (type === "bar") {
                    const BarChart = (await import('@/components/uiElements/barChart')).default;
                    root.render(<BarChart {...chartProps} graphWidth={1000} graphHeight={350} />);
                } else if(type === "line") {
                    const LineChart = (await import('@/components/uiElements/lineChart')).default;
                    root.render(<LineChart {...chartProps} graphWidth={1000} graphHeight={350} />);
                }
            } catch (e) {
                console.error("Graph data parsing error:", e);
            }
        }

        // No typing animation — directly render HTML
        if (!enableTypingAnimation) {
            botDiv.innerHTML = marked.parse(chunk);
            bubble.classList.add('done');
            inputRef.current.focus();
            return;
        }

        // Split text into words
        const words = chunk.split(/(\s+)/); // keeps spaces too
        let index = 0;
        let lastRenderTime = Date.now();

        const interval = setInterval(() => {
            if (index < words.length) {
                // Add next word as plain text (no flicker)
                botDiv.textContent += words[index];
                index++;

                const myDiv = document.getElementById('chatstreams');
                if (myDiv) {
                    myDiv.scrollTo({
                        top: myDiv.scrollHeight,
                        behavior: 'smooth',
                    });
                }

                // Every 0.3 seconds, re-render markdown for partial styling
                if (Date.now() - lastRenderTime > 300) {
                    lastRenderTime = Date.now();
                    botDiv.innerHTML = marked.parse(botDiv.textContent);
                }
            } else {
                clearInterval(interval);
                // Final markdown render
                botDiv.innerHTML = marked.parse(chunk);
                bubble.classList.add('done');
            }
        }, speed);

        inputRef.current.focus();
    };

    function getAccessTokenFromCookie() {
        const name = "access_token=";
        const decodedCookie = decodeURIComponent(document.cookie);
        const cookies = decodedCookie.split("; ");

        for (let cookie of cookies) {
            if (cookie.startsWith(name)) {
                return cookie.substring(name.length);
            }
        }

        return null; // not found
    }

    const checkCreateConvId = async (name, summary, newPrjId=false) => {
        if (convId) return convId
        const res = await fetch(`${API_HOST}/user/conversation`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ name, summary, project_id: newPrjId ? newPrjId : projectId }),
        });

        if (res.status === 200) {
            const data = await res.json();
            const { _id } = data?.conversation || {};
            updateConvId(_id);
            console.log("Conversation ID created: ", data);
            return _id;
        } else {
            return null;
        }
    }

    const updateConvId = (convID) => {
        setConvId(convID);
        const params = new URLSearchParams(window.location.search);
        params.set('convId', convID);
        if (!convID) params.delete('convId')
        router.replace(`?${params.toString()}`, { scroll: false });
        const project = allProjects.find(p => p.chats && p.chats.length > 0 && p.chats.some(chat => chat._id === convID));
        if (project && convID) loadProjectDataSources(project)
    }
    
    const initWebSocket = (currConvId) => {
        return new Promise((resolve, reject) => {
            if (!currConvId) return reject(new Error("Missing conversation ID"));
            if (window.chatSocket !== null && window.chatSocket) {
                return resolve(window.chatSocket); // already connected
            }

            const proto = window.location.protocol;
            const isLiveEnv = proto === "https:";
            const WP_HOST = process.env.WS_HOST || "localhost:8765/ws";
            let url = isLiveEnv
                ? `wss://${WP_HOST}/web_chat/`
                : `ws://${WP_HOST}/web_chat/`;

            const token = getAccessTokenFromCookie();
            if (!token) return reject(new Error("WebSocket initialization failed: No token"));

            url += `?token=${token}`;
            if (currConvId) url += `&convId=${currConvId}`;
            if (projectId) url += `&projectId=${projectId}`;

            const socket = new WebSocket(url);

            socket.onopen = () => {
                console.log("WebSocket open");
                window.chatSocket = socket;
                resolve(socket);
            };

            socket.onmessage = (e) => {
                if (e.data === "__END__") {
                    inputRef.current.disabled = false;
                    sendButtonRef.current.disabled = false;
                    setCurrentBotDiv(null);
                    setLoading((prev) => ({ ...prev, isLoading: false }));
                    inputRef.current.focus();
                } else {
                    const data = JSON.parse(e.data);
                    const { agent_responses = [], error_code = null } = data || {};
                    if (error_code) return handleWsErrors(error_code);
                    if (agent_responses && agent_responses.length > 0) {
                        for (const response of agent_responses) {
                            const { graph_data, steps=[], messages = [], followup = "", content = "", prompt_id } = response;
                            console.debug("steps:", steps);
                            console.debug("messages:", messages);
                            console.debug("graph_data:", graph_data);
                            appendBotMessage({
                                promptId: prompt_id,
                                chunk: `${content}${followup ? '\n\n' + followup : ''}`,
                                graph_data: graph_data,
                                speed: 20,
                                enableTypingAnimation: true
                            });
                        }
                    }
                    inputRef.current.focus();
                }
            };

            socket.onerror = (err) => {
                console.error("WS error", err);
                window.chatSocket = null;
                reject(err);
            };

            socket.onclose = (event) => {
                if (event.code === 4000) {
                    setChatError("No statements found for this conversation. upload to continue.");
                }
                console.log("WebSocket closed: ", event?.reason || "No reason provided");
                window.chatSocket = null;
                reject(new Error(event?.reason || "WebSocket closed"));
            };
        });
    };

    const handleWsErrors = (error_code) => {
        let errorMessage = "An error occurred.";
        if (error_code === 429) {
            errorMessage = "Rate limit exceeded. Please try again later.";
        } else if (error_code === 402) {
            errorMessage = "Credit required. Please upgrade your plan.";
        }
        toast.error(errorMessage, {
            position: "top-right",
            autoClose: 5000,
        });
        window.chatSocket = null;
    }

    const uploadFile = async (file) => {
        let currConvId = await checkCreateConvId();
        await initWebSocket(currConvId);
        setChatError(false);
        if (!file) return;
        setIsChatting(true);
        setLoading({...loading, isLoading: true});
        const form = new FormData();
        form.append('file', file);
        form.append('convId', currConvId);
        const ext = file.name.split('.').pop().toLowerCase();
        const isPdf = file.type === 'application/pdf' || ext === 'pdf';
        const isCsv = file.type === 'text/csv' || ext === 'csv';

        let uploadPath;
        if (isCsv) uploadPath = `${API_HOST}/upload`;
        else if (isPdf) uploadPath = `${API_HOST}/upload-invoice`;
        else {
            appendMessage(`<div class="chat-bubble user-bubble file-upload-bubble">Unsupported file type.</div>`, 'user-message');
            return;
        }

        try {
            const res = await fetch(uploadPath, { method: 'POST', body: form });
            const { status, message } = await res.json();
            if (status === 'success') {
                appendMessage(`<div class="chat-bubble user-bubble file-upload-bubble">File uploaded: ${file.name}</div>`, 'user-message');
            } else uploadStatusRef.current.textContent = "Error: " + message;
        } catch {
            appendMessage(`<div class="chat-bubble user-bubble file-upload-bubble">Upload failed: ${file.name}</div>`, 'user-message');
        }
        setLoading({...loading, isLoading: false});
    };

    const createMessageJsonString = (message, agentsList) => {
        return JSON.stringify({
            agents_selected: agentsList,
            message:message
        })
    }

    const parseBeforePolling = (msg) => {
        // parse the msg string for explicit @agent
        const agentPattern = /@(\w+)/g;
        const agents = [];
        let match;
        while ((match = agentPattern.exec(msg)) !== null) {
            agents.push(match[1]);
        }
        // remove the @agent from the msg
        const parsedMsg = msg.replace(agentPattern, '').trim();
        inputRef.current.value = parsedMsg;
        return agents;        
    }

    const handleSendClick = async () => {
        const msg = inputRef.current.value.trim();
        // parse the msg string for explicit @agent
        const agentsSelected = parseBeforePolling(msg);
        let agentSet = new Set([...selectedAgents, ...agentsSelected]);
        let agentsList = Array.from(agentSet);
        if (!msg) return;
        inputRef.current.value = '';
        setChatError(false);
        setLoading({...loading, isLoading: true});
        setIsChatting(true);
        appendMessage(`<div class="chat-bubble user-bubble">${msg}</div>`, 'user-message');
        let currConvId = await checkCreateConvId();
        await initWebSocket(currConvId);
        // check if currConvId exists, if not create it
        if (!currConvId) return await handleNewProjectClick("First Project", true);
        if (!window.chatSocket) return console.error("WebSocket not initialized");
        window.chatSocket.send(createMessageJsonString(msg, agentsList));
        inputRef.current.disabled = true;
        sendButtonRef.current.disabled = true;
    };
    
    const loadProjectDataSources = (project) => {
        if (!project) return
        let sources = []
        if (project.stripe_key) sources.push("stripe");
        if (project.paypal_client_id && project.paypal_client_secret) sources.push("paypal");
        if (project.xero_refresh_key) sources.push("xero");
        if (project.quickbooks_refresh_key) sources.push("quickbooks");
        setDataSources(sources);
    }

    const chatSuggested = (e) => {
        document.querySelector('#maininput').value = e.target.textContent
    }

    const handleToggleAddConnection = () => {
        setShowAddConnection(!showAddConnection);
    };
    
    const handleCloseAddConnection = () => {
        setShowAddConnection(false);
        // Clear URL params if needed
        const paramsToRemove = ["code", "state", "scope", "stripe_status", "connect"];
        const pageUrl = new URL(window.location.href);
        paramsToRemove.forEach((param) => {pageUrl.searchParams.delete(param)});
        window.history.replaceState({}, '', pageUrl.pathname + pageUrl.search);
    };

    const insertAgentMention = (agentName) => {
        const agentSet = new Set(selectedAgents);
        agentSet.add(agentName)
        setSelectedAgents(Array.from(agentSet));
        const input = inputRef.current;
        const cursorPos = input.selectionStart;
        const textBeforeMention = input.value.substring(0, mentionStartIndex);
        const textAfterMention = input.value.substring(cursorPos);
        
        const newText = textBeforeMention + '@' + agentName + ' ' + textAfterMention;
        input.value = newText;
        
        // Set cursor position after the inserted mention
        const newCursorPos = mentionStartIndex + agentName.length + 2;
        setTimeout(() => {
            input.focus();
            input.setSelectionRange(newCursorPos, newCursorPos);
        }, 0);
        
        // Trigger input event to update height and button state
        const event = new Event('input', { bubbles: true });
        input.dispatchEvent(event);
        
        setShowAgentSuggestions(false);
    };

    const loadAvailableAgents = async () => {
        const res = await fetch(`${API_HOST}/web_chat/agents?projectId=${projectId}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });

        if (res.status === 200) {
            const data = await res.json();
            const { available_agents } = data || {};
            setAvailableAgents(available_agents || []);
        }
    }

    return (
        <>
            <div className={`chatbot_container ${isChatting ? "_chatting" : ""}`}>
                {!isChatting && <>
                    <h1 className="chatBot_title">Ask Statement </h1>
                    <p className="chatBot_description">From numbers to plain decisions. Try cashflow, expenses, or runway.</p>
                </>}
                <div id="chatstreams" className="chat-messages-area" ref={chatContainerRef}></div>
                <div className="chatBot_field">
                    <p>Use shift + return for new line</p>
                    {chatError && <div className="chat-error">{chatError}</div>}
                    {loading?.isLoading && <div id="loading" ref={loadingRef} className="loading-indicator">{loadingMessage[loadingIndex]}</div>}
                    <div className="chatBot_field_wrap">
                        <div className="input-container">
                            <textarea ref={inputRef} id="maininput" type="text" placeholder="Ask me about cashflow, expenses, or runway..." className="chat-input" onInput={handleInput}/>
                            {showAgentSuggestions && filteredAgents.length > 0 && (
                                <div className="agent-suggestions-popup">
                                    {filteredAgents.map((agent, idx) => (
                                        <div 
                                            key={idx}
                                            className="agent-suggestion-item"
                                            onClick={() => insertAgentMention(agent.agent_name)}
                                        >
                                            <div className="agent-name">{agent.agent_name}</div>
                                            {agent.description && <div className="agent-description">{agent.description}</div>}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="chatBot_field_button">
                            {/* <button><img src="/next_images/microphone.svg"/></button> */}
                            <button ref={uploadIconRef}><img src="/next_images/Attach.svg"/></button>
                            <button className={(loading.isLoading && isChatting) ? 'pause':''} id="mainsendbutton" onClick={handleSendClick} ref={sendButtonRef}>
                                {loading.isLoading && isChatting ?
                                    <img src="/next_images/pause.svg"/>
                                    : 
                                    <svg xmlns="http://www.w3.org/2000/svg" width="21" height="20" viewBox="0 0 21 20" fill="none">
                                        <path d="M3.5 10H17.5M11.4972 14.9261L17.576 9.9253M11.5 5L17.5823 9.92534" stroke="#a0a0a0" strokeWidth="1.8" strokeLinecap="round"/>
                                    </svg>
                                }
                            </button>
                        </div>
                    </div>
                    <input ref={attachFileRef} className='d_none' type="file" id="attachFile" accept=".pdf,.csv" />
                    <div className="chatBot_connection">
                        <button className="chatBot_connected_button">Connected to</button>
                        {dataSources.includes("stripe") &&<div className='_item' title="Stripe"><img src="/next_images/stripe.png" alt="Stripe" /></div>}
                        {dataSources.includes("paypal") &&<div className='_item' title="Paypal"><img src="/next_images/paypal.svg" alt="Paypal" /></div>}
                        {dataSources.includes("xero") &&<div className='_item' title="Xero"><img src="/next_images/xero.svg" alt="Xero" /></div>}
                        {dataSources.includes("csv") &&<div className='_item'><img src="/next_images/csv.png" alt="CSV File" /></div>}
                        {dataSources.includes("quickbooks") &&<div className='_item'><img src="/next_images/quickbooks.png" alt="QuickBooks" /></div>}
                        {plaidConnAccounts && plaidConnAccounts.map((accnt, idx) => 
                            <div className='_item' key={idx} title={accnt?.institution?.name}>
                                {accnt.institution?.logo
                                    ? <img src={accnt.institution.logo} alt={accnt?.institution?.name}/>
                                    : <img src="/next_images/bank.svg" alt="Bank Account or Credit Card" />
                                }
                            </div>
                        )}
                        <button className="chatBot_add_button" onClick={handleToggleAddConnection}>
                            <img src="/next_images/add.svg" alt="Add connection"/>
                        </button>
                    </div>
                </div>
            </div>
            {(!isChatting && suggestedData.length > 0) && 
                <div className="chat_suggested_q">
                    <div className="chat_suggested_tab">
                        {suggestedQuestion?.[suggestedData]?.map((q , index) => (
                            <span key={index} className={index == 0 ? 'active': ''} >{q.title}</span>
                        ))}
                    </div>
                    <div className="chat_suggested_q_wrap">
                        <div className="suggested_question_wrap">
                            {randomQuestions?.map((q, index) => (
                                <div className="_question" key={index} onClick={(e) => chatSuggested(e)}>
                                    {q}
                                </div>
                            ))}
                        </div>
                        <span>Or type your own question in the input above</span>
                    </div>
                </div>
            }
            {showAddConnection && (
                <AddConnection 
                    dataSources={dataSources}
                    stripeCode={stripeCode}
                    xeroCode={xeroCode}
                    qbCode={qbCode}
                    qbRealmId={qbRealmId}
                    zohoCode={zohoCode}
                    onClose={handleCloseAddConnection}
                />
            )}
            <div className="bottom-left-toast">
                {activeSync && (
                    <div className="_item">
                        <div className="_progress-item">
                            <div className="_top">
                                <div className="_left">Syncing {activeSync.service.charAt(0).toUpperCase() + activeSync.service.slice(1)}</div>
                                <div className="_right">
                                    {activeSync.total_steps > 1 &&
                                        `Step ${activeSync.current_step} / ${activeSync.total_steps}`
                                    }
                                </div>
                            </div>
                            <div className="_middle">
                                <div className="_progress">
                                    <div
                                        className="_indicator"
                                        style={{ width: `${(activeSync.current_step / activeSync.total_steps) * 100}%` }}
                                    />
                                </div>
                            </div>
                            <div className="_bottom">
                                {`Processing ${activeSync.step?.replace(/_/g, " ")}...`}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </>
    )
}