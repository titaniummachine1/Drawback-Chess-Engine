import React, { useEffect, useState, useRef } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    createTheme,
    ThemeProvider,
    Typography,
    DialogActions,
    Button,
    Grid,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { fetchWrapper } from './Helpers';
import { DrawbackDisplay, DrawbackDifficultyScale, DrawbackDifficultyScaleForTwoPlayers } from './DrawbackGlossary';

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
    },
});

/*
    WHITE_WINS = 'white wins'
    BLACK_WINS = 'black wins'
    WHITE_WINS_ON_TIME = 'white wins on time'
    BLACK_WINS_ON_TIME = 'black wins on time'
    AGREEMENT = 'agreement'
    FIFTY_MOVE_RULE = 'fifty move rule'
    THREEFOLD_REPETITION = 'threefold repetition'
*/

const WHITE_WINS_OUTCOMES = ['white wins', 'white wins on time', 'white wins by resignation']
const BLACK_WINS_OUTCOMES = ['black wins', 'black wins on time', 'black wins by resignation']
const DRAW_OUTCOMES = ['agreement', 'fifty move rule', 'threefold repetition']

export function onRematch(gameId, navigate, showError, username, handleClose, port) {
    fetchWrapper(`/${gameId}/rematch`, { username: username }, 'POST', port)
        .then((response) => {
            if (response.success) {
                handleClose();
                navigate(`/game/${response.game.id}/${response.color}`);
                window.location.reload();
            } else {
                showError(response.error);
            }
        })
}

export function onBackToLobby(gameId, navigate, rejoinQueue) {
    fetchWrapper(`/${gameId}/decline_rematch`, {}, 'POST').then(() => {
        if (rejoinQueue) {
            navigate('/rejoin_queue');
        } else {
            navigate('/');
        }
        window.location.reload();
    })
}

function signedNumber(number) {
    return number > 0 ? `+${number}` : number;
}

export default function GameOverDialog({ open, handleClose, result, color, allKingsExist, kingWasCapturedEnPassant, handicaps, gameId, rematchGameId, showError, showMessage, username, handicapElos, handicapEloAdjustments, showRejoinQueue, spectating, smallScreen, port, haveSeenOpponentDrawback, setHaveSeenOpponentDrawback }) {
    const won = (color === 'white' && WHITE_WINS_OUTCOMES.includes(result)) || (color === 'black' && BLACK_WINS_OUTCOMES.includes(result));
    const lost = (color === 'white' && BLACK_WINS_OUTCOMES.includes(result)) || (color === 'black' && WHITE_WINS_OUTCOMES.includes(result));
    const draw = DRAW_OUTCOMES.includes(result);
    const aborted = result === 'aborted';
    const whiteWon = WHITE_WINS_OUTCOMES.includes(result);
    const blackWon = BLACK_WINS_OUTCOMES.includes(result);

    const [allHandicaps, setAllHandicaps] = useState([])

    useEffect(() => {
        if (result) {
            fetchWrapper('/handicap_glossary', { username: username }, 'GET')
                .then(response => {
                    if (response.success) {
                        setAllHandicaps(response.handicaps);
                    } else {
                        console.error('Error fetching data: ', response.error);
                    }
                });
        }
    }, [result]);

    let sentence = ''
    if (won) {
        if (['white wins on time', 'black wins on time'].includes(result)) {
            sentence = 'Your opponent ran out of time.'
        }
        else if (['white wins by resignation', 'black wins by resignation'].includes(result)) {
            sentence = 'Your opponent resigned.'
        }
        else if (allKingsExist) {
            sentence = 'Your opponent lost due to their drawback.'
        }
        else {
            sentence = "You took your opponent's king" + (kingWasCapturedEnPassant ? ' en passant.' : '.')
        }
    }
    else if (lost) {
        if (['white wins on time', 'black wins on time'].includes(result)) {
            sentence = 'You ran out of time.'
        }
        else if (['white wins by resignation', 'black wins by resignation'].includes(result)) {
            sentence = 'You resigned.'
        }
        else if (allKingsExist) {
            sentence = 'You lost due to your drawback.'
        }
        else {
            sentence = "Your opponent took your king" + (kingWasCapturedEnPassant ? ' en passant.' : '.')
        }
    }
    else if (draw) {
        if (result === 'agreement') {
            sentence = 'You and your opponent agreed to a draw.'
        }
        else if (result === 'fifty move rule') {
            sentence = 'You and your opponent drew due to the fifty-move rule.'
        }
        else if (result === 'threefold repetition') {
            sentence = 'You and your opponent drew due to threefold repetition.'
        }
    }
    else if (aborted) {
        sentence = 'The game was aborted.'
    }
    else if (whiteWon) {
        if (result === 'white wins on time') {
            sentence = 'White won on time.'
        }
        else if (result === 'white wins by resignation') {
            sentence = 'White won by resignation.'
        }
        else if (allKingsExist) {
            sentence = "White won due to Black's drawback."
        }
        else {
            sentence = "White took Black's king" + (kingWasCapturedEnPassant ? 'en passant.' : '.')
        }
    }
    else if (blackWon) {
        if (result === 'black wins on time') {
            sentence = 'Black won on time.'
        }
        else if (result === 'black wins by resignation') {
            sentence = 'Black won by resignation.'
        }
        else if (allKingsExist) {
            sentence = "Black won due to White's drawback."
        }
        else {
            sentence = "Black took White's king" + (kingWasCapturedEnPassant ? 'en passant.' : '.')
        }
    }
    else {
        sentence = ""
    }

    const opponentHandicap = handicaps?.[color === 'white' ? 'black' : 'white']
    const myHandicap = handicaps?.[color]

    const myHandicapPrefix = myHandicap?.split(':')?.[0];
    const myHandicapObj = myHandicapPrefix ? allHandicaps.find(h => h.name === myHandicapPrefix) : null;

    const navigate = useNavigate();

    const navigateBackToLobby = () => {
        navigate('/');
    }

    if (open && opponentHandicap && !haveSeenOpponentDrawback) {
        setHaveSeenOpponentDrawback(true);
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle variant="h4" style={{ textAlign: 'center' }}>{won ? 'You won!' : lost ? 'You lost.' : draw ? 'Draw' : aborted ? 'Game aborted.' : whiteWon ? 'White won.' : blackWon ? 'Black won.' : 'Game over.'}</DialogTitle>
                <DialogContent style={{ margin: '20px' }}>
                    <DialogContentText variant="h6" style={{ textAlign: 'center' }}>
                        {sentence}
                    </DialogContentText>
                    <br />
                    {['white', 'black'].includes(color) && <Typography variant="h6" style={{ textAlign: 'center' }}>
                        {'Your opponent\'s drawback was '}
                        <span style={{ fontWeight: 'bold' }}>
                            {`"${opponentHandicap}."`}
                        </span>
                    </Typography>}
                    {
                        handicapElos && handicapElos?.white != null && ['white', 'black'].includes(color) && (
                            <>
                                <br />
                                <DrawbackDifficultyScaleForTwoPlayers yourElo={handicapElos?.[color]} yourColor={color} opponentElo={handicapElos?.[color === 'white' ? 'black' : 'white']} opponentColor={color === 'white' ? 'black' : 'white'} infrequentNotches={smallScreen} />
                                <br />
                                <br />
                                <Typography variant="body1" style={{ textAlign: 'center' }}>
                                    Drawback difficulty ratings are calculated adaptively using an elo system. Your games help us determine how difficult each drawback is!
                                </Typography>
                            </>
                        )
                    }
                    {!spectating && allHandicaps && myHandicapObj &&
                        <>
                            <br />
                            <br />
                            <Typography variant="body1" style={{ textAlign: 'center' }}>
                                Did you like your drawback?
                            </Typography>
                            <br />
                            {/* <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                                <Grid container alignItems="center" justifyContent="center">
                                    <DrawbackDisplay handicap={myHandicapObj} handicaps={allHandicaps} setHandicaps={setAllHandicaps} />
                                </Grid>
                            </div> */}
                            <div style={{ display: 'flex' }}> {/* Adjust the max-width as needed */}
                                {!spectating && allHandicaps && myHandicapObj &&
                                    <DrawbackDisplay handicap={myHandicapObj} handicaps={allHandicaps} setHandicaps={setAllHandicaps} small={smallScreen} showMessage={showMessage} />
                                }
                            </div>
                        </>
                    }
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={() => onRematch(gameId, navigate, showError, username, handleClose, port)}>Rematch</Button>
                    <Button variant="contained" onClick={() => onBackToLobby(rematchGameId, navigate)}>Back to lobby</Button>
                    {showRejoinQueue && <Button variant="contained" onClick={() => onBackToLobby(rematchGameId, navigate, true)}>Join Queue</Button>}
                    <Button variant="contained" onClick={handleClose}>Ok</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}

export function RematchDeclinedDialog({ open, handleClose, rematchGameId }) {
    const navigate = useNavigate();

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle style={{ textAlign: 'center' }}>Rematch Declined</DialogTitle>
                <DialogContent>
                    <DialogContentText style={{ textAlign: 'center' }}>
                        Your opponent declined your rematch request.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={() => { handleClose(); onBackToLobby(rematchGameId, navigate); }}>Back to lobby</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}