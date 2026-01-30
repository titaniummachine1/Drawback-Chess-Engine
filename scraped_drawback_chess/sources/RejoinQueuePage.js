import { useEffect, useState } from "react";
import { fetchWrapper } from "./Helpers";
import { useNavigate } from "react-router-dom";
import { getUsername } from "./Helpers";
import Toast from "./Toast";

export default function RejoinQueuePage({ }) {
    let navigate = useNavigate();
    let [error, setError] = useState(null);
    let [message, setMessage] = useState(null);
    console.log('Mounted RejoinQueuePage');

    const showError = (message) => {
        setError(message);

        setTimeout(() => {
            setError(null);
        }, 5000);
    };

    const showMessage = (message) => {
        setMessage(message);

        setTimeout(() => {
            setMessage(null);
        }, 5000);
    };

    useEffect(() => {
        let timePreference = localStorage.getItem('time-preference');
        let timePreferenceIsStrong = localStorage.getItem('time-preference-is-strong') === 'true';
        let username = getUsername(20);
        if (timePreference === 'any') {
            timePreference = null;
        }
        fetchWrapper('/join_queue', { username, timePreference, timePreferenceIsStrong }, 'POST')
            .then((response) => {
                if (response.success || response.error === 'Already in queue') {
                    navigate('/');
                } else {
                    showError(`Failed to join queue because ${response.error}`);
                    setTimeout(() => {
                        navigate('/');
                    }, 4000);
                }
            })
    }, []);


    return <div style={{ width: '100%', display: 'flex', justifyContent: 'center', position: 'fixed', left: 0, top: 10 }}>
        {error && <Toast message={error} onClose={() => setError(null)} />}
        {message && <Toast message={message} onClose={() => setMessage(null)} isError={false} />}
    </div>
} 