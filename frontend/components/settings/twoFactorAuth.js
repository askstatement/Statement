import "@/style/component/twoFactorAuth.scss";
import { useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";

const API_HOST = process.env.API_HOST || "http://localhost:8765/api";

export default function TwoFactorAuth({ closePopup, saveChange, twoFactorAuthValue }) {
  const [step, setStep] = useState(1);
  const [token, setToken] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [tokenError, setTokenError] = useState("");
  const [qr, setQr] = useState();
  const [showSecret, setShowSecret] = useState(false);
  const [copied, setCopied] = useState(false);

  const timeoutRef = useRef(null);

  useEffect(() => {
    if (step < 1 || step > 4) {
      closePopup();
      setStep(1);
    }
    setTokenError("")
  }, [step]);

  useEffect(() => {
    if(twoFactorAuthValue == 'disable') setStep(3)
    fetch2faData();
  }, []);

  const fetch2faData = async () => {
    const res = await fetch(`${API_HOST}/settings/2fa_setup`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    });

    const data = await res.json();
    if (data.qrCode) setQr(data.qrCode);
    setSecretKey(data.secret)
  };

  const verifyCode = async () => {
    try {
      const res = await fetch(`${API_HOST}/settings/2fa_verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ token, twoFactorAuthValue }),
      });      

      if (res.status == 200) {
        if(twoFactorAuthValue == 'enable') setStep(4)
        else closePopup()
        saveChange("2FA Settings",twoFactorAuthValue)
        setTokenError(" ")
      } else {
        setTokenError("Invalid Code")
      }
    } catch (err) {
      console.error(`Error updating Two-Factor Authentication :`, err);
    }
  };

  const continueClick = async () => {
    if (step < 3 || step == 4) {
      setStep(step + 1);
    } else {
      verifyCode();
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

  const handleCopy = (key) => {
    copyToClipboard(key);
    setCopied(true);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      setCopied(false);
      timeoutRef.current = null;
    }, 3000);
  };  
  

  return (
    <div className="popup_2fa_overlay" onClick={(e) => e.stopPropagation()}>
      <div className="popup_2fa">
        <img
          className="close"
          src="/next_images/close.svg"
          onClick={() => {
            closePopup()
            setTokenError("")
          }}
        />
        <div className="popup_content">
          {step == 1 && (
            <>
              <h2>1. Download App</h2>
              <p>Download Authy or Google Authenticator app</p>
              <div className="apps_2fa">
                <div className="app_wrap">
                  <img
                    className="app_logo"
                    src="/next_images/google_authenticator.svg"
                  />
                  <h3>Google Authenticator</h3>
                  <div>
                    <button
                      onClick={() =>
                        window.open(
                          "https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2&hl=en_IN&gl=US"
                        )
                      }
                    >
                      <img src="/next_images/android.svg" />
                      Android
                    </button>
                    <button
                      onClick={() =>
                        window.open(
                          "https://apps.apple.com/us/app/google-authenticator/id388497605"
                        )
                      }
                    >
                      <img src="/next_images/ios.svg" />
                      IOS
                    </button>
                  </div>
                </div>
                <div className="app_wrap">
                  <img className="app_logo" src="/next_images/authy.svg" />
                  <h3>Authy</h3>
                  <div>
                    <button
                      onClick={() =>
                        window.open(
                          "https://play.google.com/store/apps/details?id=com.authy.authy&hl=en"
                        )
                      }
                    >
                      <img src="/next_images/android.svg" />
                      Android
                    </button>
                    <button
                      onClick={() =>
                        window.open(
                          "https://apps.apple.com/us/app/twilio-authy/id494168017"
                        )
                      }
                    >
                      <img src="/next_images/ios.svg" />
                      IOS
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}
          {step == 2 && (
            <>
              <h2>2. Scan QR Code</h2>
              <p>Go to the scan option in the app and scan this QR code</p>
              <img className="qr_code" src={qr} />
              {showSecret ? 
                <div className="secret_key_wrap">
                  <p>If you’re unable to scan QR code, enter this code manually into the app.</p>
                  <div>
                    <span>{secretKey}</span>
                    <button onClick={() => handleCopy(secretKey)}>
                      <img src="/next_images/copy.svg"/>
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                </div>
                :
                <a className="cant_scan" onClick={() => setShowSecret(true)}>I can’t scan QR Code</a>
              }
            </>
          )}
          {step == 3 && (
            <>
              <h2>3. Enter Authentication Code</h2>
              <p>Enter the authentication code generated by the app</p>
              <div className="twofactor_code">
                <input
                  type="text"
                  placeholder="Enter Code"
                  maxLength={6}
                  inputMode="numeric"
                  pattern="[0-9]*"
                  onChange={(e) => setToken(e.target.value)}
                  onInput={(e) => {
                    e.target.value = e.target.value.replace(/[^0-9]/g, "");
                  }}
                />
              </div>
              <span className="_error">{tokenError}</span>
            </>
          )}
          {step == 4 && (
            <div className="success_secret">
              <h2>Save your backup code</h2>
              <p>Keep this code safe, you will be asked for it if you lose access to your authenticator app.</p>
              <div>
                <span>{secretKey}</span>
                <button onClick={() => handleCopy(secretKey)}>
                  <img src="/next_images/copy.svg"/>
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>
          )}
        </div>
        <div className={`buttons_2fa ${twoFactorAuthValue} ${step == 4 ? 'success' : ''}`}>
          <div className="_improvement">
            <p>
              <span>{step}</span>/3
            </p>
            <div>
              <span className={`step-${step}`}></span>
            </div>
          </div>
          <div className="_buttons">
            <button onClick={() => setStep(step - 1)}>Back</button>
            <button onClick={continueClick}>
              {step == 3 ? `${twoFactorAuthValue} 2FA` : "Continue"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
