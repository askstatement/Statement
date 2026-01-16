"use client";
import { useEffect, useRef, useState } from "react";
import { Fragment } from "react";
import { toast } from "react-toastify";

// context
import { useProjectContext } from "@/context/ProjectContext";

// utils
import { formatDate } from "@/utils/dateUtils";

const API_HOST = process.env.API_HOST || "http://localhost:8765/api";

export default function ApiScreen() {
  const { project: projectContext } = useProjectContext();
  const { project } = projectContext;

  const [showAddApiKey, setShowAddApiKey] = useState(false);
  const [apiKeys, setAPIKeys] = useState([]);
  const [newApiKeyName, setNewApiKeyName] = useState("");
  const [deletePopup, setDeletePopup] = useState(false);
  const [deleteKey, setDeleteKey] = useState("");
  const [showApiKey, setShowApiKey] = useState(null);
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (project?._id) loadProjectAPIKeys();
  }, [project]);

  useEffect(() => {
    if (showAddApiKey && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showAddApiKey]);


  const removeAPIKey = async (projectId, apiKeyId) => {    
    const res = await fetch(`${API_HOST}/user/project/api_key?projectId=${projectId}&apiKeyId=${apiKeyId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      }
    });
    if (res.ok) {
      setDeletePopup(false)
      loadProjectAPIKeys();
    }
  };

  const createAPIKey = async () => {
    if (!project || !project._id) return;
    
    const res = await fetch(`${API_HOST}/user/project/api_key`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        projectId: project._id,
        name: newApiKeyName,
      }),
    });
    if (res.ok) {
      setShowAddApiKey(false);
      setNewApiKeyName("");
      loadProjectAPIKeys();
    }
  };

  const loadProjectAPIKeys = async () => {
    if (!project || !project._id) return;
    const res = await fetch(
      `${API_HOST}/user/project/api_key?projectId=${project._id}`,
      {
        method: "GET",
      }
    );

    if (res.ok) {
      let data = await res.json();
      let { keys } = data;
      setAPIKeys(keys);
    }
  };

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
  };

  const handleCopy = (apiKey) => {
    copyToClipboard(apiKey);
    setCopied(true);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      setCopied(false);
      timeoutRef.current = null;
    }, 2000);
  };  

  return (
    <div className="setting_api_key settings_section" id="api">
      <h2 className="settings_title">API Keys</h2>
      <div className="api_keys_wrap">
        <div className="create_key">
          <h3>Create API Key</h3>
          <button
            className="create_new-key-btn"
            onClick={() => setShowAddApiKey(true)}
          >
            <img src="/next_images/add.svg" />
            Create API Key
          </button>
        </div>
        <p>
          Use this API key to securely access Statement services and integrate
          with your applications.
        </p>
        {showAddApiKey && (
          <div className="settings_add_apikey-content">
            <img
              className="close_button"
              onClick={() => setShowAddApiKey(false)}
              src="/next_images/close.svg"
            />
            <h3>Create New API Key</h3>
            <p>API Key Name</p>
            <input
              ref={inputRef}
              type="text"
              placeholder="e.g., Production API Key"
              value={newApiKeyName}
              onChange={(e) => setNewApiKeyName(e.target.value)}
              maxLength="40"
            />
            <div className="button_wrap">
              <button onClick={() => setShowAddApiKey(false)}>Cancel</button>
              <button
                className={newApiKeyName == 0 ? "disabled" : ""}
                onClick={createAPIKey}
              >
                Create API Key
              </button>
            </div>
          </div>
        )}
        <table className="api_keys_table">
          <thead>
            <tr>
              <th className="name">Name</th>
              <th className="api-key">Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {apiKeys &&
              apiKeys.map((key, index) => (
                <Fragment key={index}>
                  <tr>
                    <td className="name">{key.name}</td>
                    <td className="api-key">{formatDate(key.created_at, "MMM DD, YYYY")}</td>
                    <td className="delete_button_wrap">
                      <button onClick={() => setShowApiKey(showApiKey === key.api_key ? null : key.api_key)}>
                        {showApiKey === key.api_key ? "Hide" : "Show Key"}
                      </button>
                      <button
                        className="delete_button"
                        onClick={() => {
                          setDeleteKey(key._id)
                          setDeletePopup(true)
                        }}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="16"
                          height="16"
                          viewBox="0 0 16 16"
                          fill="none"
                        >
                          <path
                            d="M14 3.98958C11.78 3.76958 9.54667 3.65625 7.32 3.65625C6 3.65625 4.68 3.72292 3.36 3.85625L2 3.98958"
                            stroke="white"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                          <path
                            d="M5.66406 3.31594L5.81073 2.4426C5.9174 1.80927 5.9974 1.33594 7.12406 1.33594H8.87073C9.9974 1.33594 10.0841 1.83594 10.1841 2.44927L10.3307 3.31594"
                            stroke="white"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                          <path
                            d="M12.563 6.09375L12.1297 12.8071C12.0564 13.8537 11.9964 14.6671 10.1364 14.6671H5.85635C3.99635 14.6671 3.93635 13.8537 3.86302 12.8071L3.42969 6.09375"
                            stroke="white"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                          <path
                            d="M6.88281 11H9.10281"
                            stroke="white"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                          <path
                            d="M6.33594 8.33594H9.66927"
                            stroke="white"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </button>
                    </td>
                  </tr>
                  {showApiKey === key.api_key && (
                    <tr className="api_key_row">
                      <td colSpan={3}>
                        <div className="api_key_copy">
                          <h3>{key.name}</h3>
                          <p>
                            Keep this key secure and never share it publicly.
                            You can use it to authenticate API requests to
                            Statement.
                          </p>
                          <div className="key_value">
                            <span>{key.api_key}</span>
                            <button
                              onClick={() =>
                                handleCopy(
                                  key.api_key
                                )
                              }
                              disabled={copied}
                              className="copy-btn"
                            >
                              <img
                                src={`/next_images/${
                                  copied ? "api_copied" : "copy"
                                }.svg`}
                                alt="Copy API key"
                              />
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
          </tbody>
        </table>
        {apiKeys && apiKeys.map((key, index) => (
          <div  key={index} className="api_details_mobile">
            <div className="api_key_wrap">
              <div className="api_details">
                <div>
                  <h4>{key.name}</h4>
                  <span>Created</span>
                  <p>{formatDate(key.created_at, "MMM DD, YYYY")}</p>
                </div>
                <button
                  className="delete_button"
                  onClick={() => {
                    setDeleteKey(key._id)
                    setDeletePopup(true)
                  }}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                  >
                    <path
                      d="M14 3.98958C11.78 3.76958 9.54667 3.65625 7.32 3.65625C6 3.65625 4.68 3.72292 3.36 3.85625L2 3.98958"
                      stroke="white"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M5.66406 3.31594L5.81073 2.4426C5.9174 1.80927 5.9974 1.33594 7.12406 1.33594H8.87073C9.9974 1.33594 10.0841 1.83594 10.1841 2.44927L10.3307 3.31594"
                      stroke="white"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M12.563 6.09375L12.1297 12.8071C12.0564 13.8537 11.9964 14.6671 10.1364 14.6671H5.85635C3.99635 14.6671 3.93635 13.8537 3.86302 12.8071L3.42969 6.09375"
                      stroke="white"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M6.88281 11H9.10281"
                      stroke="white"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M6.33594 8.33594H9.66927"
                      stroke="white"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
              <button onClick={() => setShowApiKey(showApiKey === key.api_key ? null : key.api_key)}>
                {showApiKey === key.api_key ? "Hide" : "Show Key"}
              </button>
            </div>
            {showApiKey === key.api_key && (
              <div className="api_key_copy">
                <h3>{key.name}</h3>
                <p>
                  Keep this key secure and never share it publicly. You can use it
                  to authenticate API requests to Statement.
                </p>
                <div className="key_value">
                  <span>{key.api_key}</span>
                  <button
                    onClick={() =>
                      handleCopy(key.api_key)
                    }
                    disabled={copied}
                    className="copy-btn"
                  >
                    <img
                      src={`/next_images/${copied ? "api_copied" : "copy"}.svg`}
                      alt="Copy API key"
                    />
                    Copy API
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        <p>
          Please treat your API key like a password, and keep it secret. This
          key provides access to your Statement account and services.
        </p>
        <a className="learn_more" href="/docs/api/" target="_blank">
          <img src="/next_images/learn_more.svg" />
          <p>Learn more</p>
        </a>
        {deletePopup && (
          <div className="overlay">
            <div className="delete_api">
              <img
                className="close_button"
                onClick={() => setDeletePopup(false)}
                src="/next_images/close.svg"
              />
              <h3>Delete API Key</h3>
              <p>
                Are you sure you want to delete this API key? This action cannot
                be undone.
              </p>
              <div className="delete_api_key_info">
                Any applications using this key will no longer be able to access
                the API. Make sure to update your integrations before deleting.
              </div>
              <div className="button_wrap">
                <button onClick={() => setDeletePopup(false)}>Cancel</button>
                <button onClick={() => removeAPIKey(project._id, deleteKey)}>
                  Delete API Key
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
