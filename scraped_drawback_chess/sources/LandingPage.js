import React, { useEffect, useState } from 'react';
import notifySound from './assets/notify.mp3';
import { fetchWrapper, getUsername, playNotifySound } from './Helpers';
import { useNavigate } from 'react-router-dom';
import Toast from './Toast';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import './LandingPage.css';
import Grid from '@mui/material/Grid';
import { AddFriendDialog, friendLinkDialog } from './AddFriendDialog';
import { useParams } from 'react-router-dom';
import HowToPlayDialog from './HowToPlayDialog';
import { FriendLinkDialog } from './AddFriendDialog';
import { PlayVsFriendDialog } from './PlayVsFriendDialog';
import io from 'socket.io-client';
import { baseURL } from './Settings';
import AcceptChallengeDialog from './AcceptChallengeDialog';
import SeedEloDialog from './SeedEloDialog';
import PlayerInfo from './PlayerInfo';
import { HostGameDialog } from './HostGameDialog';
import { FormControl, FormControlLabel, Select, MenuItem, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, TextField, createTheme, ThemeProvider, Checkbox } from '@mui/material';
import { Link } from 'react-router-dom';

function log(str) {
    localStorage.getItem('log') && console.log(str);
}

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
    },
});

function joinQueue(username, showError, showMessage, setQueueTimer, timePreference, timePreferenceIsStrong) {
    if (timePreference === 'any') {
        timePreference = null;
    }
    fetchWrapper('/join_queue', { username, timePreference , timePreferenceIsStrong }, 'POST')
        .then((response) => {
            if (response.success) {
                showMessage('Joined queue');
                setQueueTimer(response.queueTimer);
            } else {
                showError(response.error);
            }
        })
}

function leaveQueue(username, showError, showMessage, setQueueTimer) {
    fetchWrapper('/leave_queue', { username }, 'POST')
        .then((response) => {
            if (response.success) {
                showMessage('Left queue');
                setQueueTimer(null);
            } else {
                showError(response.error);
            }
        })
}

function LandingPageButton({ text, onClick, greenBlue, smallScreen }) {
    return (
        <Button
            variant="contained"
            style={{
                fontSize: smallScreen ? '16px' : '20px',
                padding: smallScreen ? '16px' : '20px',
                background: greenBlue ? 'linear-gradient(45deg, #90EE90 30%, #87CEFA 90%)' : 'linear-gradient(45deg, #FE6B8B 30%, #FF8E53 90%)',
                border: '2px solid black',
                transition: 'transform 0.3s ease-in-out', // Add transition for smooth effect
                color: 'black', // Change font color to black
                fontFamily: 'Roboto, sans-serif', // Use 'Roboto' font
                width: '100%',
            }}
            onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.1)'} // Scale up on hover
            onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'} // Scale down when hover ends
            onClick={onClick}
        >
            {text}
        </Button>
    )
}

function formatTime(time) {
    const date = new Date(time * 1000);
    if (time === null) {
        return null;
    }
    if (time < 0) {
        return '0:00';
    }
    let minutes = Math.floor(time / 60);
    let seconds = Math.floor(time % 60);
    return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
}


function timeSince(queueTimer) {
    if (!queueTimer) {
        return null;
    }
    const date = new Date(queueTimer * 1000);
    const now = new Date();
    const secondsAgo = Math.floor((now - date) / 1000);

    return formatTime(secondsAgo);
};

function FeedbackDialog({ open, handleClose, username, showError, showMessage, setHowToPlayDialogOpen }) {
    const [feedback, setFeedback] = useState('')

    const handleSubmitFeedback = () => {
        fetchWrapper('/feedback', { username, feedback }, 'POST')
            .then((response) => {
                if (response.success) {
                    showMessage('Feedback submitted!');
                    handleClose();
                } else {
                    showError(response.error);
                }
            })
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle>Feedback/Bug reports</DialogTitle>
                <DialogContent>
                    <DialogContentText style={{ marginBottom: '10px' }}>
                        Thank you for providing feedback or reporting a bug! We are also happy to hear ideas for new drawbacks. Please describe your issue or idea below. You can also reach us on our discord server, linked at the top of the page.
                    </DialogContentText>
                    <DialogContentText style={{ marginBottom: '10px' }}>
                        If you think you found a bug, please make sure you've read the <span style={{ color: '#1E90FF', cursor: 'pointer' }} onClick={() => setHowToPlayDialogOpen(true)}>How to Play</span> page - many "bug" reports we've gotten are explained in there!
                    </DialogContentText>
                    <DialogContentText style={{ marginBottom: '10px' }}>
                        If your feedback is about a specific game, please include a link to the game - it makes a lot easier to investigate. Thanks!
                    </DialogContentText >
                    <TextField
                        autoFocus
                        margin="dense"
                        id="name"
                        label="Feedback"
                        type="text"
                        fullWidth
                        multiline
                        rows={4}
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose} color="primary">
                        Cancel
                    </Button>
                    <Button onClick={handleSubmitFeedback} color="primary">
                        Submit
                    </Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    )
}

function SupportDialog({ open, handleClose }) {
    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle>Support Us</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        We're thrilled you're playing our game! Playing it and sharing it with your friends and family is extremely appreciated. But if you'd like to go above and beyond to support us and our continued work on the game, you can do so at <Link external="true" to="https://ko-fi.com/glydergames" target="_blank" rel="noopener noreferrer" style={{ color: '#1E90FF' }}>ko-fi.com/glydergames</Link>. 
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose} color="primary">
                        Close
                    </Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    )
}

function JoinMailingListDialog({ open, handleClose, username, showError, showMessage }) {
    const [email, setEmail] = useState('')

    const handleSubmitEmail = () => {
        fetchWrapper('/feedback', { username, feedback: email, isEmail: true }, 'POST')
            .then((response) => {
                if (response.success) {
                    showMessage('Thanks for joining our mailing list!');
                    handleClose();
                } else {
                    showError(response.error);
                }
            })
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle>Join Mailing List</DialogTitle>
                <DialogContent>
                    <DialogContentText style={{ marginBottom: '10px' }}>
                        We have more games in the works! If you'd like to be notified when we release new games, please enter your email below.
                    </DialogContentText>
                    <TextField
                        autoFocus
                        margin="dense"
                        id="name"
                        label="Email"
                        type="text"
                        fullWidth
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault(); // Prevent the default action to avoid submitting the form
                                handleSubmitEmail();
                            }
                        }}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose} color="primary">
                        Cancel
                    </Button>
                    <Button onClick={handleSubmitEmail} color="primary">
                        Submit
                    </Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    )
}

function ack({ username, messageId, isFeedback, showError, showMessage, messages, setMessages }) {
    fetchWrapper('/messages/ack', { isFeedback, username, messageId }, 'POST')
        .then((response) => {
            if (response.success) {
                showMessage('Message dismissed');
                setMessages(messages.filter((message) => message.id !== messageId));
            } else {
                showError(response.error);
            }
        })
}

function Messages({ messages, username, showError, showMessage, setMessages }) {
    if (messages.length === 0) {
        return null;
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
            {messages.slice(0, 3).map((message, index) => {
                return (
                    <div key={index} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '20px' }}>
                        <Typography>{message.feedback ? <div style={{ textAlign: 'center' }}> Response (in white) to your feedback (in yellow)
                            <div style={{ color: 'yellow' }}>{message.feedback}</div> <div> {message.message} </div> </div> : message.message}</Typography>
                        <Button style={{ marginTop: '5px' }} variant="contained" onClick={() => ack({ username, messageId: message.id, isFeedback: message.isFeedback, showError, showMessage, messages, setMessages })}>Dismiss</Button>
                    </div>
                )
            })}
        </div>
    )
}

function JoinQueueDialog({ open, handleClose, username, showError, showMessage, setQueueTimer, timePreference, setTimePreference, timePreferenceIsStrong, setTimePreferenceIsStrong, rememberTimePreference, setRememberTimePreference }) {
    let [allTimeControls, setAllTimeControls] = useState(null);
    let [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchWrapper('/time_preferences', {}, 'GET')
            .then((response) => {
                if (response.success) {
                    setAllTimeControls(response.timePreferences);
                    setLoading(false);
                } else {
                    showError(response.error);
                    setLoading(false);
                }
            })
    }, []);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault(); // Prevent the default action to avoid submitting the form
                joinQueue(username, showError, showMessage, setQueueTimer, timePreference, timePreferenceIsStrong);
                handleClose();
            }
        }

        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        }
    }, [username, timePreference, showError, showMessage, setQueueTimer]);

    if (loading) {
        return null;
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle>Join Queue</DialogTitle>
                {allTimeControls && <DialogContent style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                    <DialogContentText style={{ fontWeight: 'bold', textAlign: 'center' }}>
                        You may or may not get your time preference
                    </DialogContentText>
                    <br />
                    <DialogContentText style={{ textAlign: 'center' }}>
                        You can adjust your preferences from your profile. We'll remember your preference for when you queue in the future.
                    </DialogContentText>
                    <br />
                    <FormControlLabel
                        control={
                            <Checkbox
                                checked={rememberTimePreference}
                                onChange={() => setRememberTimePreference(!rememberTimePreference)}
                                color="primary"
                            />
                        }
                        label="Don't show this dialog again"
                    />
                    <FormControlLabel
                        control={
                            <Checkbox
                                checked={timePreferenceIsStrong}
                                onChange={() => setTimePreferenceIsStrong(!timePreferenceIsStrong)}
                                color="primary"
                            />
                        }
                        label="Only match me with exactly my time preference"
                    />
                    <FormControl style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '20px', marginTop: '20px' }}>
                        <Typography>Time Preference</Typography>
                        <Select value={timePreference} onChange={(e) => setTimePreference(e.target.value)}>
                            <MenuItem value={"any"}>Any</MenuItem>
                            {allTimeControls.map((timeControl, index) => {
                                return <MenuItem key={index} value={timeControl.name}>{timeControl.minutes}+{timeControl.increment}</MenuItem>
                            })}
                        </Select>
                    </FormControl>
                </DialogContent>
                }
                <DialogActions>
                    <Button variant="contained" onClick={() => { handleClose(); joinQueue(username, showError, showMessage, setQueueTimer, timePreference, timePreferenceIsStrong) }}>Join</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    )

}

export default function LandingPage() {
    let [howToPlayDialogOpen, setHowToPlayDialogOpen] = useState(false);
    let [seedEloDialogOpen, setSeedEloDialogOpen] = useState(false);
    let [friendLinkDialogOpen, setFriendLinkDialogOpen] = useState(false);
    let [addFriendDialogOpen, setAddFriendDialogOpen] = useState(false);
    let [playVsFriendDialogOpen, setPlayVsFriendDialogOpen] = useState(false);
    
    let [acceptChallengeDialogOpen, setAcceptChallengeDialogOpen] = useState(false);
    let [challengerDisplayName, setChallengerDisplayName] = useState('');
    let [challengeGameId, setChallengeGameId] = useState(null);
    let [challengeFriendshipId, setChallengeFriendshipId] = useState(null);
    let [challengeFromPolling, setChallengeFromPolling] = useState(false);


    let [hostGameAiDialogOpen, setHostGameAiDialogOpen] = useState(false);
    let [joinQueueDialogOpen, setJoinQueueDialogOpen] = useState(false);
    let [timePreference, setTimePreference] = useState(localStorage.getItem('time-preference') || 'any');
    let [timePreferenceIsStrong, setTimePreferenceIsStrong] = useState(localStorage.getItem('time-preference-is-strong') === 'true');
    let [rememberTimePreference, setRememberTimePreference] = useState(localStorage.getItem('remember-time-preference-2') === 'true');
    let [queueTimer, setQueueTimer] = useState(null);
    let [queue, setQueue] = useState([]);
    let [formattedTimeSince, setFormattedTimeSince] = useState(null);
    let [playerInfoOpen, setPlayerInfoOpen] = useState(false);
    let [feedbackDialogOpen, setFeedbackDialogOpen] = useState(false);
    let [joinMailingListDialogOpen, setJoinMailingListDialogOpen] = useState(false);
    let [supportDialogOpen, setSupportDialogOpen] = useState(false);
    let [messages, setMessages] = useState([]);
    let navigate = useNavigate();
    let [error, setError] = useState(null);
    let [message, setMessage] = useState(null);
    let [socket, setSocket] = useState(null);
    let [smallScreen, setSmallScreen] = useState(window.innerWidth < 1200);
    let [rejoinGameInfo, setRejoinGameInfo] = useState(null);
    const [maintenanceSoon, setMaintenanceSoon] = useState(false);
    const [maintenanceMessage, setMaintenanceMessage] = useState(null);
    const username = getUsername(20, () => setSeedEloDialogOpen(true));

    let showHidden = localStorage.getItem('showHidden');

    useEffect(() => {
        let now = new Date() / 1000;
        fetchWrapper('/now', {}, 'GET')
            .then((response) => {
                if (response.success) {
                    let latency = new Date() / 1000 - now;
                    let diff = response.now - new Date() / 1000 - (latency / 2);
                    if (!(-3 < diff < 3)) {
                        showError("Your computer's time looks off from the server. You may experience issues with your clock. Please check your system time or go to time.is to see if there's a difference.")
                    } 
                }
                else {
                    console.error(response.error);
                }
            });
    }, []);

    useEffect(() => {
        fetchWrapper('/rejoin_game', { username }, 'GET')
            .then((response) => {
                if (response.success) {
                    setRejoinGameInfo(response);
                } else {
                    showError(response.error);
                }
            })
    }, [username]);

    // disconnect socket when unmounting
    useEffect(() => {
        return () => {
            log('disconnecting socket');
            socket && socket.disconnect();
        }
    }, [socket]);

    useEffect(() => {
        username && fetchWrapper('/make_user', { username }, 'POST')
            .then((response) => {
                response.error && showError(response.error);
                setQueueTimer(response.queueTimer);
            })
    }, [username])

    useEffect(() => {
        localStorage.setItem('time-preference', timePreference);
    }, [timePreference]);

    useEffect(() => {
        localStorage.setItem('remember-time-preference-2', rememberTimePreference);
    }, [rememberTimePreference]);

    useEffect(() => {
        localStorage.setItem('time-preference-is-strong', timePreferenceIsStrong);
    }, [timePreferenceIsStrong]);

    let port = 5050;

    useEffect(() => {
        fetchWrapper('/poll_for_challenge', { username }, 'GET', port)
        .then((response) => {
            if (response.success && response.challengerDisplayName) {
                setAcceptChallengeDialogOpen(true);
                setChallengerDisplayName(response.challengerDisplayName);
                setChallengeGameId(response.gameId);
                setChallengeFriendshipId(response.friendshipId);
                setChallengeFromPolling(true);
            } else {
                showError(response.error);
            }
        })
    }, [username])

    useEffect(() => {
        let maintenanceSilenced = localStorage.getItem('maintenanceSoonSilenced');

        if (maintenanceSilenced) {
            let { silenced, expires } = JSON.parse(maintenanceSilenced);

            if (silenced && new Date().getTime() < expires) {
                maintenanceSilenced = false;
            } else {
                localStorage.removeItem('maintenanceSoonSilenced');
            }
        }

        if (maintenanceSilenced) {
            return;
        }

        fetchWrapper('/maintenance', {}, 'GET')
            .then((response) => {
                if (response && response.success && setMaintenanceSoon) {
                    setMaintenanceSoon(response.maintenance);
                    if (response.message) {
                        setMaintenanceMessage(response.message);
                    }
                } else {
                    console.error(response.error);
                }
            });
    }, [])

    const ONE_HOUR = 60 * 60 * 1000; // One hour in milliseconds

    function handleCloseMaintenanceToast() {
        const currentTime = new Date().getTime();
        const expirationTime = currentTime + ONE_HOUR; // Set expiration time to one hour from current time

        setMaintenanceSoon(false);
        localStorage.setItem('maintenanceSoonSilenced', JSON.stringify({ silenced: true, expires: expirationTime }));
    }

    // try to reconnect to the socket if it's lost
    useEffect(() => {
        if (socket) {
            socket.on('disconnect', () => {
                setTimeout(() => {
                    setSocket(null);
                }, 1000);
            });
        }

        return () => {
            if (socket) {
                socket.off('disconnect');
            }
        }
    }, [socket]);

    // connect to socket if null on loop
    useEffect(() => {
        const interval = setInterval(() => {
            if (!socket) {
                if (process.env.REACT_APP_LOCAL) {
                    setSocket(io.connect(process.env.REACT_APP_FULL_URL))
                } else {
                    setSocket(io.connect(baseURL, { transports: ['websocket'], path: `/app${port - 5000}/socket.io` }));
                }
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [socket, port]);

    useEffect(() => {
        fetchWrapper('/messages', { username }, 'GET')
            .then((response) => {
                if (response.success) {
                    setMessages(response.messages);
                } else {
                    showError(response.error);
                }
            })
    }, [username]);

    let { friendshipId } = useParams();

    const showError = (message) => {
        setError(message);

        setTimeout(() => {
            setError(null);
        }, 5000);
    }

    const showMessage = (message) => {
        setMessage(message);

        setTimeout(() => {
            setMessage(null);
        }, 5000);
    }

    useEffect(() => {
        if (friendshipId != null) {
            setAddFriendDialogOpen(true);
        }
    })

    useEffect(() => {
        if (socket) {
            log('setting socket username', username)
            socket.emit('join', { room: username })
        }

        return () => {
            log('leaving room ', username)
            socket && socket.emit('leave', { room: username })
        }
    }, [username, socket])

    useEffect(() => {
        if (!socket) {
            log('no socket yet')
            return;
        }

        log('adding socket callbacks')

        socket.on('connect', () => {
            if (username) {
                log('joining on connect');
                socket.emit('join', { room: username });
            }
        }, [username]);

        socket.on('message', (data) => {
            log('received message: ', data['msg'])
            showMessage(data['msg']);
        });

        socket.on('challenge', (data) => {
            log('received challenge: ', data)

            setAcceptChallengeDialogOpen(true);
            setChallengerDisplayName(data.displayName);
            setChallengeGameId(data.gameId);
            setChallengeFriendshipId(data.friendshipId);
            setChallengeFromPolling(false);
        });

        socket.on('request_ack', (data) => {
            let gameId = data.gameId;
            let color = data.color;
            fetchWrapper('/ack', { username, gameId, color }, 'POST', 5050)
                .then((response) => {
                    response.error && showError(response.error);
                }
                )
        }
        );

        socket.on('challenge_accepted', (data) => {
            playNotifySound(notifySound, 100);
            navigate(`/game/${data.gameId}/${data.color}`);
        });

        return () => {
            if (!socket) {
                return
            }
            socket.off('challenge');
            socket.off('challenge_accepted');
            socket.off('request_ack');
        }
    }, [socket]);

    useEffect(() => {
        let interval = setInterval(() => {
            setFormattedTimeSince(timeSince(queueTimer));
        }, 1000);

        return () => {
            clearInterval(interval);
        }
    }, [queueTimer]);

    useEffect(() => {
        let interval = setInterval(() => {
            if (queueTimer) {
                fetchWrapper('/queue_user', { username }, 'GET')
                    .then((response) => {
                        if (response.success) {
                            if (!response.queueTimer) {
                                setTimeout(() => {
                                    showError('Something went wrong and you were removed from the queue - sorry! Feel free to rejoin.');
                                }, 2000);
                                setQueueTimer(null);
                            } else {
                                setQueueTimer(response.queueTimer);
                            }
                        } else {
                            showError(response.error);
                        }
                    })
            }
        }, 3000);

        return () => {
            clearInterval(interval);
        }
    }, [!!queueTimer]);

    useEffect(() => {
        let interval = setInterval(() => {
            if (!showHidden) {
                return;
            } else {
                fetchWrapper('/queue', {}, 'GET')
                    .then((response) => {
                        if (response.success) {
                            setQueue(response.queue);
                        } else {
                            showError(response.error);
                        }
                    })
            }
        }, 3000);

        return () => {
            clearInterval(interval);
        }
    }, []);

    useEffect(() => {
        function handleResize() {
            setSmallScreen(window.innerWidth < 1200);
        }

        window.addEventListener('resize', handleResize);

        return () => window.removeEventListener('resize', handleResize);
    }, []);

    function clickQueue() {
        if (queueTimer && formattedTimeSince) {
            leaveQueue(username, showError, showMessage, setQueueTimer);
        } else if (rememberTimePreference) {
            joinQueue(username, showError, showMessage, setQueueTimer, timePreference, timePreferenceIsStrong);
        } else {
            setJoinQueueDialogOpen(true);
        }
    }

    return (
        <>
            <div style={{ width: '100%', display: 'flex', justifyContent: 'center', position: 'fixed', left: 0 }}>
                {error && <Toast message={error} onClose={() => setError(null)} />}
                {message && <Toast message={message} onClose={() => setMessage(null)} isError={false} />}
            </div>
            {maintenanceSoon && <div style={{ width: '100%', display: 'flex', justifyContent: 'center', position: 'fixed', left: 0, top: 40 }}>
                <Toast message={maintenanceMessage || "We will be restarting our servers and rolling out new features and fixes soon. You may experience frequent interruptions."} isError={true} onClose={handleCloseMaintenanceToast} />
            </div>}
            <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: smallScreen ? 'calc(100vh - 110px)' : 'calc(100vh - 40px)', marginLeft: '20px', marginRight: '20px' }}>
                <div style={{ justifyContent: 'center', display: 'flex', flexDirection: 'column', marginBottom: '10px', marginTop: '20px' }}>
                    <Typography style={{ fontFamily: 'Bungee Spice', textAlign: 'center', fontSize: smallScreen ? '1em' : '3em', marginBottom: smallScreen ? '0.2em' : '-0.2em', padding: smallScreen ? '5px' : '10px' }}>DRAWBACK CHESS</Typography>
                    <Typography style={{ textAlign: 'center', marginBottom: '10px', fontSize: smallScreen ? '1em' : '1.5em', fontFamily: 'Arial', fontWeight: 'bold', zIndex: 1000 }}>
                        Check out our <Link external="true" to="https://discord.gg/FZ34XU7q2U" target="_blank" rel="noopener noreferrer" style={{ color: '#1E90FF' }}>Discord server</Link> and <Link external="true" to="https://x.com/glyder_games" target="_blank" rel="noopener noreferrer" style={{ color: '#1E90FF' }}>Twitter</Link>!
                    </Typography>
                    <Link external="true" to="https://store.steampowered.com/app/3074200/The_Rookery/" target="_blank" rel="noopener noreferrer">
                        <img 
                            src={`${process.env.PUBLIC_URL}/assets/rookery_banner.jpg`} 
                        alt="Rookery Banner" 
                        style={{ 
                            width: '100%', 
                            maxWidth: '300px', 
                            height: 'auto', 
                            marginBottom: '10px',
                            display: 'block',
                            marginLeft: 'auto',
                            marginRight: 'auto',
                            animation: "pulseSize 2s infinite",                                
                            }} 
                        />
                    </Link>
                    <Typography className="bobbing" style={{ 
                        textAlign: 'center', 
                        marginBottom: '10px', 
                        fontSize: smallScreen ? '0.7em' : '1.25em', 
                        fontFamily: 'Arial', 
                        fontWeight: 'bold', 
                        zIndex: 1000, 
                        animation: "pulseSize 2s infinite",
                        color: '#FFFACD'  // Light yellow color (LemonChiffon)
                    }}>
                        And check out our new <Link external="true" to="https://store.steampowered.com/app/3074200/The_Rookery/" target="_blank" rel="noopener noreferrer" style={{ color: '#1E90FF' }}>chess roguelite</Link>, available <Link external="true" to="https://store.steampowered.com/app/3074200/The_Rookery/" target="_blank" rel="noopener noreferrer" style={{ color: '#1E90FF' }}>on Steam now!</Link> 
                    </Typography>
                    <Typography className="bobbing" style={{ 
                        textAlign: 'center', 
                        marginBottom: '10px', 
                        fontSize: smallScreen ? '0.5em' : '1em', 
                        fontFamily: 'Arial', 
                        fontWeight: 'bold', 
                        zIndex: 1000,
                        color: '#FFFACD'  // Light yellow color (LemonChiffon)
                    }}>
                        Build a powerful chess army with unique relics and boosts, and face eleven different bosses, each with unfair advantages of its own!
                    </Typography>
                    <Messages messages={messages} setMessages={setMessages} username={username} showError={showError} showMessage={showMessage} />
                    {rejoinGameInfo && rejoinGameInfo.gameId && <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '20px' }}>
                        <Typography>It looks like you have a game in progress. Would you like to rejoin it?</Typography>
                        <Button style={{ marginTop: '5px' }} variant="contained" onClick={() => navigate(`/game/${rejoinGameInfo.gameId}/${rejoinGameInfo.color}`)}>Rejoin</Button>
                    </div>}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', width: '100%', maxWidth: '600px', margin: '0 auto' }}>
                    <Grid container item spacing={smallScreen ? 2 : 3} justifyContent="center" alignItems="center" direction="column">
                        <Grid container item spacing={3} justifyContent="center" direction="row">
                            <Grid item xs={6} style={{ display: 'flex', justifyContent: 'flex-start', width: '50%' }}>
                                <LandingPageButton text={(queueTimer && formattedTimeSince) ? `Leave Queue ${formattedTimeSince}` : "Join Queue"} onClick={clickQueue} smallScreen={smallScreen} />
                            </Grid>
                            <Grid item xs={6} style={{ display: 'flex', justifyContent: 'flex-end', width: '50%' }}>
                                <LandingPageButton greenBlue text="How to Play" onClick={() => setHowToPlayDialogOpen(true)} smallScreen={smallScreen} />
                            </Grid>
                        </Grid>
                        <Grid container item spacing={3} justifyContent="center" direction="row">
                            <Grid item xs={6} style={{ display: 'flex', justifyContent: 'flex-start', width: '50%' }}>
                                <LandingPageButton text="Play vs Friend" onClick={() => setPlayVsFriendDialogOpen(true)} smallScreen={smallScreen} />
                            </Grid>
                            <Grid item xs={6} style={{ display: 'flex', justifyContent: 'flex-end', width: '50%' }}>
                                <LandingPageButton greenBlue text="Add Friend" onClick={() => setFriendLinkDialogOpen(true)} smallScreen={smallScreen} />
                            </Grid>
                        </Grid>
                        <Grid container item spacing={3} justifyContent="center" direction="row">
                            <Grid item xs={6} style={{ display: 'flex', justifyContent: 'flex-start', width: '50%' }}>
                                <LandingPageButton text="Play vs AI" onClick={() => setHostGameAiDialogOpen(true)} smallScreen={smallScreen} />
                            </Grid>
                            <Grid item xs={6} style={{ display: 'flex', justifyContent: 'flex-end', width: '50%' }}>
                                <LandingPageButton greenBlue text="Drawback Glossary" onClick={() => navigate('/glossary')} smallScreen={smallScreen} />
                            </Grid>
                        </Grid>
                        <Grid container item spacing={3} justifyContent="center" direction="row">
                            <Grid item xs={6} style={{ display: 'flex', justifyContent: 'flex-start', width: '50%' }}>
                                <LandingPageButton text="Match History" onClick={() => navigate('/match-history')} smallScreen={smallScreen} />
                            </Grid>
                            <Grid item xs={6} style={{ display: 'flex', justifyContent: 'flex-end', width: '50%' }}>
                                <LandingPageButton greenBlue text="View/Edit Profile" onClick={() => setPlayerInfoOpen(true)} smallScreen={smallScreen} />
                            </Grid>
                        </Grid>
                    </Grid>
                </div>
                {joinQueueDialogOpen && <JoinQueueDialog open={joinQueueDialogOpen} handleClose={() => setJoinQueueDialogOpen(false)} username={username} showError={showError} showMessage={showMessage} setQueueTimer={setQueueTimer} timePreference={timePreference} setTimePreference={setTimePreference} timePreferenceIsStrong={timePreferenceIsStrong} setTimePreferenceIsStrong={setTimePreferenceIsStrong} rememberTimePreference={rememberTimePreference} setRememberTimePreference={setRememberTimePreference} />}
                {seedEloDialogOpen && <SeedEloDialog open={seedEloDialogOpen} handleClose={() => { setSeedEloDialogOpen(false); setHowToPlayDialogOpen(true) }} username={username} showError={showError} showMessage={showMessage} />}
                {howToPlayDialogOpen && <HowToPlayDialog handleClose={() => setHowToPlayDialogOpen(false)} />}
                {addFriendDialogOpen && <AddFriendDialog open={addFriendDialogOpen} handleClose={() => setAddFriendDialogOpen(false)} username={username} friendshipId={friendshipId} showMessage={showMessage} showError={showError} />}
                {friendLinkDialogOpen && <FriendLinkDialog open={friendLinkDialogOpen} handleClose={() => setFriendLinkDialogOpen(false)} username={username} />}
                {playVsFriendDialogOpen && <PlayVsFriendDialog open={playVsFriendDialogOpen} handleClose={() => setPlayVsFriendDialogOpen(false)} username={username} showMessage={showMessage} showError={showError} setChallengeFriendshipId={setChallengeFriendshipId} />}
                {acceptChallengeDialogOpen && <AcceptChallengeDialog 
                    open={acceptChallengeDialogOpen} 
                    handleClose={() => setAcceptChallengeDialogOpen(false)} 
                    username={username} gameId={challengeGameId} 
                    challengerDisplayName={challengerDisplayName} 
                    friendshipId={challengeFriendshipId} 
                    showError={showError} 
                    fromPolling={challengeFromPolling}
                />}
                {playerInfoOpen && <PlayerInfo open={playerInfoOpen} handleClose={() => setPlayerInfoOpen(false)} username={username} rememberTimePreference={rememberTimePreference} setRememberTimePreference={setRememberTimePreference} showMessage={showMessage} showError={showError} />}
                {hostGameAiDialogOpen && <HostGameDialog
                    open={hostGameAiDialogOpen}
                    handleClose={() => setHostGameAiDialogOpen(false)}
                    username={username}
                    showError={showError}
                    vsAi={true}
                />}
                {showHidden && queue && queue.map((player, index) => {
                    return (
                        <div key={index} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '10px' }}>
                            <Typography style={{ fontFamily: 'Bungee Spice', fontSize: '1.5em' }}>{player}</Typography>
                        </div>
                    )
                })}
                {feedbackDialogOpen && <FeedbackDialog open={feedbackDialogOpen} handleClose={() => setFeedbackDialogOpen(false)} username={username} showError={showError} showMessage={showMessage} setHowToPlayDialogOpen={setHowToPlayDialogOpen} />}
                {joinMailingListDialogOpen && <JoinMailingListDialog open={joinMailingListDialogOpen} handleClose={() => setJoinMailingListDialogOpen(false)} username={username} showError={showError} showMessage={showMessage} />}
                {supportDialogOpen && <SupportDialog open={supportDialogOpen} handleClose={() => setSupportDialogOpen(false)} />}
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', margin: smallScreen ? '10px 0 10px' : '20px 0 10px' }}>
                    <Button variant="contained" onClick={() => setFeedbackDialogOpen(true)} style={{ marginRight: '20px', marginBottom: '10px' }}>{smallScreen ? 'Feedback' : 'Feedback/Suggestions'}</Button>
                    <Button variant="contained" onClick={() => setJoinMailingListDialogOpen(true)} style={{ marginBottom: '10px' }}>Join Mailing List</Button>
                    <Button variant="contained" onClick={() => setSupportDialogOpen(true)} style={{ marginLeft: '20px', marginBottom: '10px' }}>Support Us</Button>
                </div>
            </div>
        </>
    )
}