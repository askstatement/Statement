import "@/style/component/history.scss";
import { useEffect, useState } from "react";
import { useRouter } from 'next/navigation';

// context
import { useProjectContext } from "@/context/ProjectContext";

// utils
import { formatDateToFriendly } from "@/utils/dateUtils";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';

export default function History() {

    const router = useRouter();

    const [chats, setchats] = useState([]);

    const { project } = useProjectContext();

    useEffect(() => {
        fetchHistory();
    }, [project?.project?._id]);

    const fetchHistory = async () => {
        if (!project?.project?._id) return;

        const res = await fetch(`${API_HOST}/user/project-conversations?projectId=${project?.project?._id}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });

        if (res.ok) {
            const data = await res.json();
            setchats(data.conversations || []);
        } else {
            console.error("Failed to fetch history");
        }
    };

    const handleDeleteChat = async (ev, chat_id) => {
        ev.stopPropagation();
        ev.preventDefault();

        try {
            const resp = await fetch(`${API_HOST}/user/conversation?convId=${chat_id}`, {
                method: "DELETE",
            });
            if (resp.ok) {
                window.location.reload(); // Reload to reset chat state
                console.log("Chat deleted successfully");
            } else {
                console.error("Failed to delete chat");
            }
        } catch (error) {
            console.error("Error deleting chat:", error);
        }
    };

    const handleChatClick = (chat) => {
        // Handle chat click event
        const { _id: convId } = chat || {};
        const params = new URLSearchParams(window.location.search);
        params.set('convId', convId);
        params.set('tab', "chat");
        if (!convId) params.delete('convId')
        router.replace(`?${params.toString()}`, { scroll: false });
    }

    const groupHistory = (chats) => {
        chats.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        const group = {}
        for (const chat of chats) {
            const dateStr = formatDateToFriendly(chat.created_at)
            if (!group[dateStr]) group[dateStr] = []
            group[dateStr].push(chat)
        }
        return group || {}
    }

    const historyGrouped = groupHistory(chats)

    return (
        <div className="chat_history-container">
            <div className="_header">
                <h1 className="_title">
                    History
                </h1>
                <p className="_description">Look back at previous conversations</p>
            </div>
            {Object.keys(historyGrouped).map((day, d_idx) => 
                <div className="_section" key={d_idx}>
                    <div className="_title">
                        <span className="_heading">{day}</span>
                        <span className="_queries">{historyGrouped[day].length} queries</span>
                    </div>
                    {historyGrouped[day] && historyGrouped[day].length > 0 && historyGrouped[day].map((chat, idx) =>
                        <div className="_item" key={idx} onClick={() => handleChatClick(chat)}>
                            <div className="_left">
                                <div className="_name">{chat.name || "New chat"}</div>
                                {chat.summary && <div className="_summary">{chat.summary}</div>}
                            </div>
                            <div className="_right" onClick={(ev) => ev.stopPropagation()}>
                                <img src="/next_images/tripple-dots.svg" />
                                <div className="_wrap">
                                    <ul className="_options">
                                        <li onClick={(ev) => handleDeleteChat(ev, chat._id)}>
                                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                                                <path d="M21 5.97656C17.67 5.64656 14.32 5.47656 10.98 5.47656C9 5.47656 7.02 5.57656 5.04 5.77656L3 5.97656" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                                <path d="M8.5 4.97L8.72 3.66C8.88 2.71 9 2 10.69 2H13.31C15 2 15.13 2.75 15.28 3.67L15.5 4.97" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                                <path d="M18.8484 9.14062L18.1984 19.2106C18.0884 20.7806 17.9984 22.0006 15.2084 22.0006H8.78844C5.99844 22.0006 5.90844 20.7806 5.79844 19.2106L5.14844 9.14062" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                                <path d="M10.3281 16.5H13.6581" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                                <path d="M9.5 12.5H14.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                            Delete
                                        </li>
                                        {/* <li onClick={(ev) => ev.stopPropagation()}>
                                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                                                <path d="M16.4366 8.89844C20.0366 9.20844 21.5066 11.0584 21.5066 15.1084V15.2384C21.5066 19.7084 19.7166 21.4984 15.2466 21.4984H8.73656C4.26656 21.4984 2.47656 19.7084 2.47656 15.2384V15.1084C2.47656 11.0884 3.92656 9.23844 7.46656 8.90844" stroke="#A2A2A2" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                                <path d="M12 14.9972V3.61719" stroke="#A2A2A2" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                                <path d="M15.3484 5.85L11.9984 2.5L8.64844 5.85" stroke="#A2A2A2" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                            Share
                                        </li> */}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}