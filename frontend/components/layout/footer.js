import Link from "next/link"

export default function Footer () {
    const CurrentYear = () => {
        const year = new Date().getFullYear()
        return year
    }
    return (
        <div className="footer">
            <div className="footer_top">
                <div className="footer_logo">
                    <h3>STATEMENT</h3>
                    <p>Your Finance, Simplified by AI</p>
                </div>
                <div className="footer_menu_wrap">
                    {/* <div className="footer_news_letter">
                        <p>Newsletter</p>
                        <input/>
                        <button>Get early updates</button>
                    </div> */}
                    <div className="footer_menu">
                        <ul>
                            <p>Company</p>
                            <Link href="/contact">Contact us</Link>
                        </ul>
                        <ul>
                            <p>Legal</p>
                            <Link href="/terms">Terms of Service</Link>
                            <Link href="/privacy">Privacy Policy</Link>
                        </ul>
                    </div>
                    
                </div>
            </div>
            <div className="footer_bottom">
                <h4>© Statament. All Rights Reserved {CurrentYear()}</h4>
                <div className="footer_links">
                    <a href="https://x.com/askstatement" target="_blank">
                        <img src="/next_images/x.svg"/>
                    </a>
                </div>
            </div>
            <img className="footer_img" src="/next_images/footer_img.svg"/>
        </div>
    )
}