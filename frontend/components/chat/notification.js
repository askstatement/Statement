export default function Notification ({onClose}) {
    return (
        <div className="notification_container" onClick={(e) => e.stopPropagation()}>
            <div className="notification_title">
                <h1>Notifications </h1>
                <div>
                    <button >Clear All</button>
                    <button className="notification_button" onClick={onClose}><img src="/next_images/close.svg"/></button>
                </div>
            </div>
            <div className="_empty">No new notfications.</div>
        </div>
    )
}