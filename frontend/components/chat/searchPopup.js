"use client";
import { useRouter } from "next/navigation";
import { useState, useEffect, useCallback } from "react";

// context
import { useProjectContext } from "@/context/ProjectContext";

const API_HOST = process.env.API_HOST || "http://localhost:8765/api";

export default function SearchPopup({ closeMenu, history = [] }) {
  const router = useRouter();
  const { project } = useProjectContext();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState(history || []);
  const [loading, setLoading] = useState(false);

  const projectId = project?.project?._id || null;

  // Debounce helper
  const debounce = (fn, delay) => {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  };

  const handleChatClick = (convId) => {
    // Handle chat click event
    const params = new URLSearchParams(window.location.search);
    params.set("convId", convId);
    params.set("tab", "chat");
    if (!convId) params.delete("convId");
    // Using window.location.href to ensure the page reloads and fetches the chat
    window.location.href = `/chat?${params.toString()}`;
  };

  // API call
  const fetchResults = useCallback(
    debounce(async (searchTerm) => {
      if (!searchTerm || !projectId) {
        return;
      }
      setLoading(true);
      try {
        const res = await fetch(
          `${API_HOST}/user/conversations/search?q=${encodeURIComponent(searchTerm)}&pid=${projectId}`,
          {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );
        if (res.ok) {
          const data = await res.json();
          setResults(data.results || []);
        } else {
          console.error("Search failed:", res.status);
          setResults([]);
        }
      } catch (err) {
        console.error("Error searching:", err);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 600), // 600ms debounce
    [projectId]
  );

  useEffect(() => {
    fetchResults(query);
  }, [query, fetchResults]);

  const navigateSection = () => {
    window.location.href = "/chat?tab=chat";
    closeMenu();
  };

  return (
    <div className="searchPopup_container">
      <div className="searchPopup_wrap">
        <div className="navbar_right_search">
          <input
            placeholder="Search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <img className="search_icon" src="/next_images/search.svg" />
        </div>

        <h2 className="new_chat" onClick={navigateSection}>
          <img src="/next_images/edit.svg" />
          New Chat
        </h2>

        {loading && (
          <div className="search_suggestion">
            <div>
              <p>Searching...</p>
            </div>
          </div>
        )}

        {!loading && results.length === 0 && query && (
          <div className="search_suggestion">
            <div>
              <p>No results found</p>
            </div>
          </div>
        )}

        {!loading && results.length > 0 &&
          <div className="search_results">
            {results.map((item) => (
              <div
                key={item._id}
                className="search_suggestion"
                onClick={() => handleChatClick(item._id)}
              >
                <div>
                  <h4>{item.name}</h4>
                  <p>{item.summary}</p>
                </div>
              </div>
            ))}
          </div>
        }
      </div>
    </div>
  );
}
