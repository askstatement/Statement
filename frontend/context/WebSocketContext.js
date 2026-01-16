'use client';
import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { getAccessTokenFromCookie } from '@/utils/cookie';
import { useProjectContext } from '@/context/ProjectContext';

const WebSocketContext = createContext();

export function useWebSocket() {
    return useContext(WebSocketContext);
}

export function WebSocketProvider({ children }) {
    const [ws, setWs] = useState(null);
    const [syncProgress, setSyncProgress] = useState({});
    const progressWsRef = useRef(null);
    const { project } = useProjectContext();
    const projectId = project?.project?._id;

    const connect = useCallback((url) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            return ws;
        }

        const newWs = new WebSocket(url);
        setWs(newWs);
        return newWs;
    }, [ws]);

    const disconnect = useCallback(() => {
        if (ws) {
            ws.close();
            setWs(null);
        }
    }, [ws]);

    // In WebSocketContext.js
    const listenForSyncProgress = useCallback(() => {
        if (progressWsRef.current && progressWsRef.current.readyState < 2) {
            return;
        }
        if (!projectId) {
            return;
        }

        const jwtToken = getAccessTokenFromCookie();
        if (!jwtToken) {
            return;
        }

        const proto = window.location.protocol;
        const isLiveEnv = proto === 'https:';
        const WP_HOST = process.env.WS_HOST || 'localhost:8765/ws';
        const wsUrl = `${isLiveEnv ? 'wss' : 'ws'}://${WP_HOST}/web_chat/sync-progress?token=${jwtToken}&project_id=${projectId}`;
        

        const newProgressWs = new WebSocket(wsUrl);
        progressWsRef.current = newProgressWs;

        newProgressWs.onopen = () => {
        };

        newProgressWs.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                
                if (message.type === 'ping') return;

                if (message.service) {
                    setSyncProgress(prev => {
                        const newProgress = { ...prev, [message.service]: message };
                        
                        if (message.status === 'done' || message.status === 'error') {
                            setTimeout(() => {
                                setSyncProgress(current => {
                                    const updated = { ...current };
                                    delete updated[message.service];
                                    return updated;
                                });
                            }, 5000);
                        }
                        
                        return newProgress;
                    });
                } else {
                    console.warn('Message missing service field:', message);
                }
            } catch (error) {
                console.error('Error parsing sync progress message:', error, event.data);
            }
        };

        newProgressWs.onclose = (event) => {
            progressWsRef.current = null;
        };

        newProgressWs.onerror = (error) => {
            console.error('Sync progress WebSocket error:', error);
        };
    }, [projectId]);

    // Connect on mount and when projectId changes
    useEffect(() => {
        if (projectId) {
            listenForSyncProgress();
        }

        // Cleanup on unmount
        return () => {
            if (progressWsRef.current) {
                progressWsRef.current.close();
                progressWsRef.current = null;
            }
        };
    }, [projectId]); // ONLY depend on projectId

    const value = {
        ws,
        connect,
        disconnect,
        syncProgress,
        listenForSyncProgress,
    };

    return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}