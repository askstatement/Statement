
export default function CommingSoon(props) {

    return (
        <div className="account_connect_button">
            <button 
                className=""
                disabled={true}
            >
                {props?.connectBtnText || "Comming Soon"}
            </button>
        </div>
    )
}