import "@/style/component/newsInsights.scss"
import LineChart from "@/components/uiElements/lineChart";

export default function DummySection() {
    return (
        <div>
            <div className="news_wrap">
                <span>2025-08-16</span>
                <h1>Weekly Cashflow Check</h1>
                <p>Your cash reserved dropped by $15k this month. Consider reducingdiscreptionary spend.</p>
                <div className="news_wrap_button">
                    <button>Ask</button>
                </div>
            </div>
            <div className="news_wrap">
                <span>2025-08-16</span>
                <h1>Weekly Cashflow Check</h1>
                <p>Your cash reserved dropped by $15k this month. Consider reducingdiscreptionary spend.</p>
                <div className="news_wrap_button">
                    <button>Ask</button>
                </div>
            </div>
            <div className="news_wrap">
                <span>2025-08-16</span>
                <h1>Weekly Cashflow Check</h1>
                <p>Your cash reserved dropped by $15k this month. Consider reducingdiscreptionary spend.</p>
                <div className="news_wrap_button">
                    <button>Ask</button>
                </div>
            </div>
            <div className="news_wrap">
                <span>2025-08-16</span>
                <h1>Weekly Cashflow Check</h1>
                <p>Your cash reserved dropped by $15k this month. Consider reducingdiscreptionary spend.</p>
                <LineChart/>
            </div>
            <div className="news_wrap">
                <span>2025-08-16</span>
                <h1>Weekly Cashflow Check</h1>
                <p>Your cash reserved dropped by $15k this month. Consider reducingdiscreptionary spend.</p>
                <img src="/next_images/graph1.svg"/>
                <div className="news_wrap_button">
                    <button>Ask</button>
                </div>
            </div>
        </div>
    )
}