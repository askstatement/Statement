import "@/style/component/newsInsights.scss";
import { useState, useEffect } from "react";

// components
import DummySection from "@/components/chat/dummySection";
import WelcomePopup from "@/components/chat/welcomePopup";
import LineChart from "@/components/uiElements/lineChart";

// context
import { useProjectContext } from "@/context/ProjectContext";
import AddConnection from "./addConnection";

const API_HOST = process.env.API_HOST || 'http://localhost:8765/api';


export default function NewsInsights(props) {

    const { stripeCode } = props;

    const [insights, setInsights] = useState([]);
    const [addConnection, setAddConnection] = useState(false)
    const [loading, setLoading] = useState(true);

    const sources = []

    const { project } = useProjectContext();

    const activeProject = project && project?.project ? project.project : null

    if (activeProject && activeProject.plaid_token) sources.push("plaid");
    if (activeProject && activeProject.csv_uploaded) sources.push("csv");
    if (activeProject && activeProject.stripe_key) sources.push("stripe");
    if (activeProject && activeProject.plaid_account_details) sources.push("plaid");

    const dataConnected = sources && sources.length > 0 ? true : false;

    const fetchNotesAndInsights = async () => {
        try {
            setLoading(true)
            if (!project?.project?._id) throw new Error("Project ID is missing.");
            const res = await fetch(`${API_HOST}/user/insights?projectId=${activeProject._id}`, {
                method: "GET",
                headers: { "Content-Type": "application/json" },
            });

            if (res.ok) {
                const data = await res.json();
                let { insights } = data;
                insights = insights.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                if (insights && insights.length > 0) setInsights(insights);
                else setInsights([]);
            } else {
                console.error("Failed to fetch notes and insights.");
            }
        } catch (err) {
            console.error("Error fetching notes and insights:", err);
        } finally {
            setLoading(false); 
        }
    }

    useEffect(() => {
        if (dataConnected) {
            fetchNotesAndInsights();
        } else {
            setLoading(false); 
        }
    }, [dataConnected]);

    function formatDate(dateStr) {
        try {
            if (!dateStr) return "";
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return dateStr; // invalid date -> return as-is

            // Get today's and yesterday's dates in UTC
            const today = new Date();
            const yesterday = new Date();
            yesterday.setDate(today.getDate() - 1);

            // Normalize all dates to midnight (UTC) for comparison
            const normalize = (d) => new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
            const normalizedDate = normalize(date);
            const normalizedToday = normalize(today);
            const normalizedYesterday = normalize(yesterday);

            if (normalizedDate.getTime() === normalizedToday.getTime()) {
                return "Today";
            }
            if (normalizedDate.getTime() === normalizedYesterday.getTime()) {
                return "Yesterday";
            }

            // Otherwise, return formatted YYYY-MM-DD
            const year = date.getUTCFullYear();
            const month = String(date.getUTCMonth() + 1).padStart(2, "0");
            const day = String(date.getUTCDate()).padStart(2, "0");
            return `${year}-${month}-${day}`;
        } catch (error) {
            try {
                // Fallback: return the original string if parsing fails
                return dateStr.toISOString().split("T")[0]; 
            } catch (e) {
                return "";
            }
        }
    }

    const SkeletonInsight = () => {
        return (
            <div className="news_wrap skeleton"></div>
        )
    }


    const createConversation = async (insight_id, reason) => {
        if (!insight_id) return
        const res = await fetch(`${API_HOST}/user/conversation`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ reason: reason, insight_id: insight_id, project_id: activeProject._id }),
        });

        if (res.status === 200) {
            const data = await res.json();
            const { _id } = data?.conversation || {};
            window.location.href = `/chat?tab=chat&convId=${_id}`;
            console.log("Conversation ID created: ", data);
            return _id;
        } else {
            return null;
        }
    }

    return (
        <div className={`news_container ${dataConnected ? '_conncted' : ''}`}>
            {(!dataConnected && !loading) && (
                <>
                    <WelcomePopup stripeCode={stripeCode} openConnection={() => setAddConnection(!addConnection)}/>
                    {(addConnection || stripeCode) && (
                        <AddConnection onClose={() => setAddConnection(!addConnection)} stripeCode={stripeCode} 
                        // dataSources={dataSources}
                        />
                    )}
                </>
            )}
            {(dataConnected || loading) && (
                <div className="news_title">
                    <h1>Notes & Insights</h1>
                    <p>Chronological record of key financial questions and answers</p>
                </div>
            )}
            {(!dataConnected && !loading)  && <div className="dummySection"><DummySection /></div>}
            
            {(dataConnected || loading) && (
                <div className="insights_list">
                    {loading
                    ? Array(5).fill(0).map((_, i) => <SkeletonInsight key={i} />)
                    : insights.length > 0
                        ? insights.map((insight, index) => insightElement(index, insight, createConversation, formatDate))
                        : <DummySection />}
                </div>
            )}
        </div>
    )
}

const insightElement = (index, insight, createConversation, formatDate) => {

    let { graph_data } = insight || {};

    try {
        graph_data = JSON.parse(graph_data || {});
    } catch (_) {}

    return insight?.display_type !== "graph" ? (
      <div className="news_wrap" key={index}>
        <span>{formatDate(insight.created_at)}</span>
        <h1>{insight.title || ""}</h1>
        <p>{insight.description || ""}</p>
        <div className="news_wrap_button">
          <button onClick={() => createConversation(insight._id, "ask")}>
            Ask
          </button>
          <button onClick={() => createConversation(insight._id, "details")}>
            View Details
          </button>
        </div>
      </div>
    ) : (
      <div className="news_wrap" key={index}>
        <span className="_created">{formatDate(insight.created_at)}</span>
        <h1>{insight.title || ""}</h1>
        <p>{insight.description || ""}</p>
        <LineChart
          title={insight.title}
          xLabels={graph_data?.xaxis || []}
          data={graph_data?.yaxis || []}
        />
      </div>
    );
}
