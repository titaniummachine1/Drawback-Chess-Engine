import { useState, useEffect, useRef } from 'react';
import { fetchWrapper , getUsername } from './Helpers';
import './Styles.css';

function updateGame(id, setGame) {
    fetchWrapper('/game', { id }, 'GET')
        .then((response) => {
            if (response.success) {
                setGame(response.game);
            } else {
                console.log(response.error);
            }
        })
}

const BREAKPOINTS = [4, 11, 31];

export default function Timer({ game, setGame, color, lowTimeSound, volume, playLowTimeSound, myTimer, lag }) {
    const [time, setTime] = useState(game.timer[color]);
    const [requestUpdate, setRequestUpdate] = useState(false);
    const [breakpointsReached, setBreakpointsReached] = useState({});
    const [flash, setFlash] = useState(false);
    const [initialRender, setInitialRender] = useState(true);

    const initialRenderRef = useRef(initialRender);

    const breakpointsReachedRef = useRef(breakpointsReached);
    const timeRef = useRef(time);

    useEffect(() => {
        breakpointsReachedRef.current = breakpointsReached;
    }, [breakpointsReached]);

    useEffect(() => {
        timeRef.current = time;
    }, [time]);

    useEffect(() => {
        initialRenderRef.current = initialRender;
    }, [initialRender]);

    let displayName = game?.displayNames?.[color];

    let turn = game.turn;
    let timeRemaining = game.timer[color];
    let lastMovedTime = game.lastMove && game.lastMove.timestamp;
    let id = game.id;

    const flashTimer = () => {
        setFlash(true);
        setTimeout(() => setFlash(false), 300);
        playLowTimeSound(lowTimeSound, volume);
    }

    useEffect(() => {
        if (requestUpdate && !game.result) {
            updateGame(id, setGame);
        }
    }, [requestUpdate, id, setGame]);

    useEffect(() => {
        setTimeout(() => {
            setRequestUpdate(false);
        }, 1500);
    }, [game]);

    useEffect(() => {
        const interval = setInterval(() => {
            // If you lose internet or something and try to make a move, the clocks will just stop ticking, which maybe isn't optimal
            if (game.temporary || game.timer[color] == null) {
                return;
            } if (!game.timer.running) {
                setTime(game.timer[color]);
                return;
            }
            const now = Date.now() / 1000 + (lag || 0);
            const timeElapsed = lastMovedTime ? now - lastMovedTime : 0;
            const currentTimer = timeRemaining - (color === turn ? timeElapsed : 0);
            const coyoteTime = myTimer ? Math.min(1, Math.max(0, 1 - currentTimer / 60)) : 0;

            if (timeRemaining - (color === turn ? timeElapsed : 0) <= 0 && game.timer.running && !requestUpdate) {
                setRequestUpdate(true);
            }

            if (myTimer) {
                BREAKPOINTS.forEach((breakpoint) => {
                    if (timeRef.current <= breakpoint && !breakpointsReachedRef.current[breakpoint]) {
                        setBreakpointsReached((prevState) => ({ ...prevState, [breakpoint]: true }));
                        if (!initialRenderRef.current) {
                            flashTimer();
                        }
                    }
                });
            }

            setInitialRender(false);
            setTime(timeRemaining - coyoteTime - (color === turn ? timeElapsed : 0));
        }, 300);

        return () => clearInterval(interval);
    }, [turn, game, timeRemaining, lastMovedTime, color, game.temporary, game.timer, requestUpdate]);

    function formatTime(time) {
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

    return (
        <div className={`timer ${flash ? 'reverse-flash' : ''}`} style={{...(flash ? {} : {color: game.timer.running && game.turn === color ? 'red' : 'white'})}}>
            <div className="timer-label">{displayName}</div>
            <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
                <div className="timer-value">{formatTime(time)}</div>
                {myTimer && time && game.increment ? <div style={{ fontSize: '14px' , marginLeft: '8px' }}>(+{game.increment})</div> : null}
            </div>
        </div>
    );
};
