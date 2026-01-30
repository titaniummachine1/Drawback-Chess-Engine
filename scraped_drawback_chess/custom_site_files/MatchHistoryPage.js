import React, { useState, useEffect } from 'react';
import { Button, Grid, Typography, Card, CardContent } from '@mui/material';
import { fetchWrapper, getUsername } from './Helpers';
import { useNavigate, useParams } from 'react-router-dom';
import { Select, MenuItem } from '@mui/material';

import StaticBoard from './StaticBoard';
import { CopyButton } from './GamePage';
import Toast from './Toast';

import io from 'socket.io-client';

import AcceptChallengeDialog from './AcceptChallengeDialog';

import { baseURL } from './Settings';
import { playNotifySound } from './Helpers';
import notifySound from './assets/notify.mp3';


function GameDisplay({ game, playerInfo, showMessage, showError }) {
    const cardStyle = {
        backgroundColor: '#3a337e', // Dark blue background color
        maxWidth: '800px', // Set maximum width to fit content
        padding: '16px', // Add padding
        margin: '8px', // Add margin
        borderRadius: '64px',
        cursor: 'pointer',
        textDecoration: 'none',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        height: '100%',
        marginLeft: '15px',
    };

    const navigate = useNavigate();

    const isWhite = game?.displayNames?.white === playerInfo?.displayName;
    const gameColor = isWhite ? 'white' : 'black';

    const handleClick = () => {
        navigate(`/game/${game.id}/${gameColor}`)
    }

    return (
        <Card style={cardStyle} onClick={handleClick}>
            <CardContent>
                <Grid item container direction="column" spacing={2}>
                    <Grid item>
                        <Typography variant="h5">
                            {isWhite ? game?.displayNames?.black : game?.displayNames?.white}
                        </Typography>
                    </Grid>
                    <Grid item>
                        <Typography variant="h6">
                            {isWhite ? game?.handicaps?.black : game?.handicaps?.white}
                        </Typography>
                    </Grid>
                    <Grid item>
                        <StaticBoard
                            board={game?.board}
                            squareWidth={40}
                            display={''}
                            orientation={isWhite ? 'white' : 'black'}
                        />
                    </Grid>
                    <Grid item>
                        <Typography variant="h5">
                            {isWhite ? game?.displayNames?.white : game?.displayNames?.black}
                        </Typography>
                    </Grid>
                    <Grid item>
                        <Typography variant="h6">
                            {isWhite ? game?.handicaps?.white : game?.handicaps?.black}
                        </Typography>
                    </Grid>
                    <Grid item onClick={(e) => e.stopPropagation()}>
                        <CopyButton
                            isShareLinkButton
                            game={game}
                            showMessage={showMessage}
                            showError={showError}
                            buttonStyles={{}}
                            color={gameColor}
                        />
                    </Grid>
                </Grid>
            </CardContent>
        </Card>
    );
}

function HandicapSelector({ allHandicaps, handicap, setHandicap, fetchMatchHistory }) {
    if (!allHandicaps) return null;
    return (
        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '15px' }}>
            <Typography variant="h5">
                Drawback
            </Typography>
            <Select value={handicap} onChange={(e) => {
                setHandicap(e.target.value);
                fetchMatchHistory(e.target.value);
            }}>
                <MenuItem value={'All'}>All</MenuItem>
                {allHandicaps.map((handicap) => (
                    <MenuItem key={handicap} value={handicap}>{handicap}</MenuItem>
                ))}
            </Select>
        </div>
    );
}

export default function MatchHistoryPage() {
    const [games, setGames] = useState(null);
    const [playerInfo, setPlayerInfo] = useState(null);
    const username = localStorage.getItem('dc-username');
    const gameIndex = parseInt(useParams().gameIndex || '0');
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);
    const [allHandicaps, setAllHandicaps] = useState(null);
    const [handicap, setHandicap] = useState('All');

    let [socket, setSocket] = useState(null);

    let [acceptChallengeDialogOpen, setAcceptChallengeDialogOpen] = useState(false);
    let [challengerDisplayName, setChallengerDisplayName] = useState('');
    let [challengeGameId, setChallengeGameId] = useState(null);
    let [challengeFriendshipId, setChallengeFriendshipId] = useState(null);
    let port = 5050;

    if (localStorage.getItem('pleaseCrashMyPage')) {
        // For testing error boundary behavior
        const r = null.pleaseCrashMyPage;
    }

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
    }, [socket, process.env.REACT_APP_FULL_URL]);

    const showError = (message) => {
        if (message === 'Invalid move') return;
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


    const navigate = useNavigate();

    function update() {
        fetchWrapper('/username', { username }, 'GET')
            .then((response) => {
                if (response.success) {
                    setPlayerInfo(response.user);
                } else {
                    showError(response.error);
                }
            });
    }

    useEffect(() => {
        update();
    }, [username]);

    useEffect(() => {
        fetchMatchHistory(gameIndex, handicap);
    }, [gameIndex]);

    useEffect(() => {
        if (!socket) {
            return;
        }
        socket.on('connect', () => {
            if (username) {
                socket.emit('join', { room: username });
            }
        }, [username]);
        socket.on('challenge', (data) => {
            setAcceptChallengeDialogOpen(true);
            setChallengerDisplayName(data.displayName);
            setChallengeGameId(data.gameId);
            setChallengeFriendshipId(data.friendshipId);
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

    }, [socket])

    useEffect(() => {
        fetchWrapper('/handicap_glossary', { username }, 'GET')
            .then((response) => {
                if (response.success) {
                    setAllHandicaps(response.handicaps.map((handicap) => handicap.name));
                } else {
                    showError(response.error);
                }
            }
            );
    }, []);

    const fetchMatchHistory = async (index, handicap) => {
        let body = { gameIndex: index, username};
        if (handicap !== 'All') {
            body.handicap = handicap;
        }
        try {
            const response = await fetchWrapper(`/match_history`, body, 'GET');
            setGames(response.games);
        } catch (error) {
            showError('Error fetching match history: ' + error);
        }
    };

    const handlePagination = (increment) => {
        const newIndex = Math.max(parseInt(gameIndex) + increment, 0);
        navigate('/match-history/' + newIndex);
    };

    const noGames = ((games?.length === 0) && (gameIndex === 0));

    if (!playerInfo) {
        return null;
    }

    return (
        <>
            <Grid container direction="column" spacing={2}>
                <div style={{ width: '100%', display: 'flex', justifyContent: 'center', position: 'fixed', left: 0, top: 10, zIndex: 9999 }}>
                    {error && <Toast message={error} onClose={() => setError(null)} />}
                    {message && <Toast message={message} onClose={() => setMessage(null)} isError={false} />}
                </div>
                <Grid item>
                    <Button variant="outlined" onClick={() => navigate('/')} style={{ width: '100px', height: '100px', borderRadius: '20%', marginRight: '10px' }}>
                        <Typography style={{ fontSize: '50px' }}>
                            <span role="img" aria-label="home" style={{ fontSize: '50px' }}>🏠</span>
                        </Typography>
                    </Button>
                </Grid>
                <Grid item>
                    {gameIndex > 0 && <Button variant="outlined" onClick={() => handlePagination(-10)} style={{ width: '100px', height: '100px', borderRadius: '50%', marginRight: '10px' }}>
                        <Typography style={{ fontSize: '50px' }}>
                            <span role="img" aria-label="left-arrow" style={{ fontSize: '50px' }}>⬅️</span>
                        </Typography>
                    </Button>}
                    {games?.length >= 10 && <Button variant="outlined" onClick={() => handlePagination(10)} style={{ width: '100px', height: '100px', borderRadius: '50%', marginRight: '10px' }}>
                        <Typography style={{ fontSize: '50px' }}>
                            <span role="img" aria-label="right-arrow" style={{ fontSize: '50px' }}>➡️</span>
                        </Typography>
                    </Button>}
                </Grid>
                <Grid item>
                    <Typography variant="h3">
                        Match History
                    </Typography>
                    <HandicapSelector allHandicaps={allHandicaps} handicap={handicap} setHandicap={setHandicap} fetchMatchHistory={(handicap) => {
                        navigate('/match-history/' + 0)
                        fetchMatchHistory(0, handicap)
                    }} />
                </Grid>
                {noGames && (
                    <Grid item>
                        <Typography variant="h5">
                            Looks like you don't have any games yet!
                        </Typography>
                    </Grid>
                )}
                <Grid container spacing={2}>
                    {games && games.map((game) => (
                        <Grid item key={game.id} xs={12} sm={6} style={{ justifyContent: 'center', display: 'flex', flexDirection: 'column' }}>
                            <GameDisplay game={game} playerInfo={playerInfo} showMessage={showMessage} showError={showError} />
                        </Grid>
                    ))}
                </Grid>
                <Grid item>
                    {gameIndex > 0 && <Button variant="outlined" onClick={() => handlePagination(-10)} style={{ width: '100px', height: '100px', borderRadius: '50%', marginRight: '10px' }}>
                        <Typography style={{ fontSize: '50px' }}>
                            <span role="img" aria-label="left-arrow" style={{ fontSize: '50px' }}>⬅️</span>
                        </Typography>
                    </Button>}
                    {games?.length >= 10 && <Button variant="outlined" onClick={() => handlePagination(10)} style={{ width: '100px', height: '100px', borderRadius: '50%', marginRight: '10px' }}>
                        <Typography style={{ fontSize: '50px' }}>
                            <span role="img" aria-label="right-arrow" style={{ fontSize: '50px' }}>➡️</span>
                        </Typography>
                    </Button>}
                </Grid>
            </Grid>
            {acceptChallengeDialogOpen && <AcceptChallengeDialog
                open={acceptChallengeDialogOpen}
                handleClose={() => setAcceptChallengeDialogOpen(false)}
                username={username} gameId={challengeGameId}
                challengerDisplayName={challengerDisplayName}
                friendshipId={challengeFriendshipId}
                showError={showError}
            />}
        </>
    );
}