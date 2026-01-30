import React, { useState, useEffect, useRef, useCallback, createRef } from 'react';
import { baseURL } from './Settings';
import io from 'socket.io-client';
import { useParams } from 'react-router-dom';
import { fetchWrapper, getUsername } from './Helpers';
import { useNavigate } from 'react-router-dom';
import ClipboardJS from 'clipboard';
import Toast from './Toast';
import Button from '@mui/material/Button';
import Timer from './Timer';
import Square from './Square';
import ChessPiece from './ChessPiece';
import './Styles.css';
import { Grid, Typography } from '@mui/material';
import moveSound from './assets/move.mp3';
import captureSound from './assets/capture.mp3';
import wrongSound from './assets/wrong.mp3';
import notifySound from './assets/notify.mp3';
import lowTimeSound from './assets/low_time.mp3';
import { playMoveSound, playWrongSound, playNotifySound, playLowTimeSound } from './Helpers';
import IconButton from '@mui/material/IconButton';
import SettingsIcon from '@mui/icons-material/Settings';
import SettingsDialog from './SettingsDialog';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import GameOverDialog, { onRematch, onBackToLobby, RematchDeclinedDialog } from './GameOverDialog';
import EnrichedText from './EnrichedText';
import AcceptChallengeDialog from './AcceptChallengeDialog';
import ChessNotationText from './ChessNotationText';
import MaterialIndicator from './MaterialIndicator';

function log(str) {
    localStorage.getItem('log') && console.log(str);
}

const WORD_TOOLTIPS_LEMMA = {
    'piece': 'A piece is ANY chess piece, including pawns.',
    'adjacent': 'A square is adjacent to another square if they are adjacent diagonally OR orthogonally.',
    'distance': 'Distance is calculated by adding the horizontal and vertical distances ("Manhattan distance"); for example, the distance a knight moves is 3, and pieces move farther diagonally than orthogonally.',
    'value': 'Piece value is calculated using 1-3-3-5-9: pawns are 1, bishops and knights are 3, rooks are 5, and queens are 9. Kings have infinite value.',
    'rim': 'The rim is any square on the first rank, the last rank, the A-file, or the H-file.',
    'home': "White's 'home rank' or 'home row' is the first rank, it's 'two home ranks' are the first and second ranks, etc. And vice versa for black"
}

const WORD_TOOLTIPS = {
    'pieces': WORD_TOOLTIPS_LEMMA['piece'],
    'piece': WORD_TOOLTIPS_LEMMA['piece'],
    'adjacent': WORD_TOOLTIPS_LEMMA['adjacent'],
    'adjacency': WORD_TOOLTIPS_LEMMA['adjancent'],
    'distance': WORD_TOOLTIPS_LEMMA['distance'],
    'further': WORD_TOOLTIPS_LEMMA['distance'],
    'farther': WORD_TOOLTIPS_LEMMA['distance'],
    'closer': WORD_TOOLTIPS_LEMMA['distance'],
    'Manhattan': WORD_TOOLTIPS_LEMMA['distance'],
    'far': WORD_TOOLTIPS_LEMMA['distance'],
    'towards': WORD_TOOLTIPS_LEMMA['distance'],
    'away': WORD_TOOLTIPS_LEMMA['distance'],
    'values': WORD_TOOLTIPS_LEMMA['value'],
    'value': WORD_TOOLTIPS_LEMMA['value'],
    'valuable': WORD_TOOLTIPS_LEMMA['value'],
    'rim': WORD_TOOLTIPS_LEMMA['rim'],
    'home': WORD_TOOLTIPS_LEMMA['home'],
}

function getAllMovesFromScoresheet(scoresheet) {
    return Object.entries(scoresheet)
        .sort(([keyA], [keyB]) => parseInt(keyA) > parseInt(keyB) ? 1 : -1)
        .reduce((acc, [, value]) => acc.concat(value), []);
}

export function boardOrder(color) {
    let files = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
    let ranks = [1, 2, 3, 4, 5, 6, 7, 8];

    if (color === 'white') {
        ranks = ranks.reverse();
    } else {
        files = files.reverse();
    }


    let ret = []

    for (let rank of ranks) {
        for (let file of files) {
            ret.push(file + rank);
        }
    }

    return ret;
}

const gameResultToSummarySentence = (result, allKingsExist) => {
    return ({
        'white wins': `1-0 · ${allKingsExist ? 'Black lost due to their drawback' : "Black's king was captured"}`,
        'black wins': `0-1 · ${allKingsExist ? 'White lost due to their drawback' : "White's king was captured"}`,
        'white wins on time': '1-0 · White won on time',
        'black wins on time': '0-1 · Black won on time',
        'white wins by resignation': '1-0 · Black resigned',
        'black wins by resignation': '0-1 · White resigned',
        'agreement': `1/2-1/2 · Draw by agreement`,
        'fifty move rule': '1/2-1/2 · Draw by fifty move rule',
        'threefold repetition': '1/2-1/2 · Draw by threefold repetition',
        'aborted': 'Game aborted',
    }[result])
}

function ScoreSheet({ game, color, setGame, showError, moveSound, captureSound, volume, setPlayersInCheck, username, smallScreen, shortScreen, plyDict, setGameFromPlyDict, justArrows, hideArrows }) {
    let [fetching, setFetching] = useState(false);
    const scoreSheetRef = useRef(null);

    const getPlyFromMoveNumberAndIndex = (moveNumber, index) => {
        return moveNumber * 2 + index;
    };

    const moveRefs = useRef([]);

    function getGameCallback(ply, playSound) {
        if (plyDict[ply] && (game.result == plyDict[ply].result)) {
            setGameFromPlyDict(ply);
            if (playSound) {
                const allMoves = getAllMovesFromScoresheet(game?.scoreSheet)
                playMoveSound(moveSound, captureSound, volume, allMoves?.[game?.ply - 1]?.includes('x'));
            }
            return;
        }
        if (fetching) {
            return;
        }
        setFetching(true);
        fetchWrapper('/game', { id: game.id, color, username, ply }, 'GET', getPort(game.id))
            .then((response) => {
                if (response.success) {
                    const allMoves = getAllMovesFromScoresheet(response?.game?.scoreSheet)

                    setGame(response.game);
                    setFetching(false);
                    if (playSound) {
                        playMoveSound(moveSound, captureSound, volume, allMoves?.[response?.game?.ply - 2]?.includes('x'));
                    }
                    setPlayersInCheck(response.game.playersInCheck)
                    localStorage.getItem('log') && log(response.game)
                } else {
                    showError(response.error);
                    setFetching(false);
                }
            }
            )
    }

    let getGame = useCallback(getGameCallback, [game, setGame, showError, fetching, moveSound, captureSound, volume, setPlayersInCheck, username, plyDict]);

    const handleClick = (moveNumber, index) => {
        const ply = getPlyFromMoveNumberAndIndex(moveNumber, index)

        if (ply === game.ply) {
            return;
        } else {
            getGame(ply);
            // Scroll the selected move into view
            moveRefs.current[ply]?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
        }
    };

    const rowHeight = 40;

    const maxHeight = 280;

    const numRows = Object.keys(game.scoreSheet).length;

    const maxPly = 1 + (numRows - 1) * 2 + (game.scoreSheet[numRows]?.length || 0);

    useEffect(() => {
        if (game?.current && game?.ply === maxPly) {
            // Scroll to the bottom of the score sheet
            const scoreSheetElement = scoreSheetRef.current;
            if (scoreSheetElement) scoreSheetElement.scrollTop = scoreSheetElement.scrollHeight;
        }
    }, [game, maxPly]);

    const currentMaxHeight = Math.min(maxHeight, numRows * rowHeight);

    const goBackInScore = () => {
        if (game.ply > 2) {
            getGame(game.ply - 1, false);
            // Scroll the selected move into view
            !smallScreen && !shortScreen && moveRefs.current[game.ply - 1]?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
        }
    }

    const goForwardInScore = () => {
        if (game.ply < maxPly) {
            getGame(game.ply + 1, true);
            // Scroll the selected move into view
            !smallScreen && !shortScreen && moveRefs.current[game.ply + 1]?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
        }
    }

    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === 'ArrowLeft') {
                event.preventDefault();
                goBackInScore();
            } else if (event.key === 'ArrowRight') {
                event.preventDefault();
                goForwardInScore();
            }
        };


        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [game, getGame, maxPly]);

    if (justArrows) {
        return (
            <Grid container className="score-sheet" style={{ width: smallScreen ? '350px' : '400px', backgroundColor: '#444488', border: '2px solid #ffffff', borderRadius: '10px', marginLeft: smallScreen ? '10px' : '50px', marginRight: '10px', overflowX: 'hidden' }}>
                <Grid item container style={{ margin: '5px' }}>
                    <Grid item xs={6}>
                        <IconButton onClick={goBackInScore} disabled={game.ply <= 2} style={{ backgroundColor: '#ddd' }}>
                            <ArrowBackIcon sx={{ color: 'red' }} />
                        </IconButton>
                    </Grid>
                    <Grid item xs={6}>
                        <IconButton onClick={goForwardInScore} disabled={game.ply >= maxPly} style={{ backgroundColor: '#ddd' }}>
                            <ArrowForwardIcon sx={{ color: 'red' }} />
                        </IconButton>
                    </Grid>
                </Grid>
            </Grid>
        ) 
    }

    return (
        game?.scoreSheet?.[1]?.length > 0 ? <Grid container className="score-sheet" style={{ width: smallScreen ? '350px' : '400px', backgroundColor: '#444488', border: '2px solid #ffffff', borderRadius: '10px', marginLeft: smallScreen ? '10px' : '50px', marginRight: '10px', overflowX: 'hidden' }}>
            {!hideArrows && <Grid item container style={{ marginTop: '10px' }}>
                <Grid item xs={6}>
                    <IconButton onClick={goBackInScore} disabled={game.ply <= 2} style={{ backgroundColor: '#ddd' }}>
                        <ArrowBackIcon sx={{ color: 'red' }}/>
                    </IconButton>
                </Grid>
                <Grid item xs={6}>
                    <IconButton onClick={goForwardInScore} disabled={game.ply >= maxPly} style={{ backgroundColor: '#ddd' }}>
                        <ArrowForwardIcon sx={{ color: 'red' }}/>
                    </IconButton>
                </Grid>
            </Grid>}
            <Grid item container ref={scoreSheetRef} style={{ maxHeight: `${currentMaxHeight}px`, overflowY: 'auto', margin: '10px', overflowX: 'hidden' }}>
                {Object.entries(game.scoreSheet).map(([moveNumber, moves]) => (
                    <Grid item xs={12} key={moveNumber} className="move-row" style={{ height: `${rowHeight}px` }}>
                        <Grid container>
                            <Grid item xs={3} style={{
                                display: 'flex',
                                justifyContent: 'flex-start',
                                alignItems: 'center'
                            }}>
                                <Typography variant="body1" style={{ fontSize: '22px' }}>{`${moveNumber}.`}</Typography>
                            </Grid>
                            {moves.map((move, index) => {
                                const ply = getPlyFromMoveNumberAndIndex(moveNumber, index);
                                return (
                                    <Grid
                                        item
                                        xs={4}
                                        key={index}
                                        className={"move"}
                                        onClick={() => handleClick(moveNumber, index)}
                                        style={{
                                            cursor: 'pointer',
                                            ...(ply === game.ply ? { backgroundColor: '#004400' } : {}),
                                            display: 'flex',
                                            justifyContent: 'flex-start',
                                            alignItems: 'center',
                                        }}
                                        ref={el => moveRefs.current[ply] = el}
                                    >
                                        <ChessNotationText text={move} />
                                    </Grid>
                                )
                            })}
                        </Grid>
                    </Grid>
                ))}
            </Grid>
            <Grid container style={{ marginBottom: '10px', alignItems: 'center', justifyContent: 'center' }}>
                <Typography>
                    {game.result ? gameResultToSummarySentence(game?.result, game?.allKingsExist) : null}
                </Typography>
            </Grid>
        </Grid> : game?.result === 'aborted' ? <Grid container className="score-sheet" style={{ width: '400px', backgroundColor: '#444488', border: '2px solid #ffffff', borderRadius: '10px', marginLeft: '50px', marginRight: '10px', overflowX: 'hidden' }}>
            <Grid item container style={{ marginBottom: '10px', marginTop: '10px', alignItems: 'center', justifyContent: 'center' }}>
                <Typography>
                    Game aborted
                </Typography>
            </Grid>
        </Grid> : null
    );
}

function simpleHash(string) {
    let hash = 0;
    if (string.length === 0) return hash;

    for (let i = 0; i < string.length; i++) {
        const char = string.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    while (hash < 0) {
        hash += 2 ** 32;
    }
    return hash;
}

function getPort(gameId) {
    return process.env.REACT_APP_LOCAL ? 5001 : 5001 + simpleHash(gameId) % 16;
}

export function CopyButton({ isShareLinkButton, showMessage, showError, buttonStyles, game, color }) {
    const buttonRef = useRef(null);

    useEffect(() => {
        const clipboard = new ClipboardJS(buttonRef.current);

        clipboard.on('success', (e) => {
            showMessage('Copied to clipboard')
            e.clearSelection();
        });

        clipboard.on('error', (e) => {
            showError('Error copying to clipboard: ' + e)
        });

        return () => {
            clipboard.destroy();
        };
    }, []);

    let text = '';

    if (isShareLinkButton) {
        text = `${window.location.origin}/game/${game.id}/${color === 'white' ? 'white' : 'black'}`;
    }
    else {
        text = `${window.location.origin}/game/${game.id}/${color === 'white' ? 'black' : 'white'}`;
    }

    return (
        <Button variant="contained" ref={buttonRef} data-clipboard-text={text} style={isShareLinkButton ? { backgroundColor: 'lightpink', color: 'black' } : buttonStyles}>
            {isShareLinkButton ? 'Share Link' : 'Copy Link'}
        </Button>
    );
};

const useMousePosition = () => {
    const [
        mousePosition,
        setMousePosition
    ] = useState({ x: null, y: null });

    useEffect(() => {
        const updateMousePosition = ev => {
            setMousePosition({ x: ev.clientX, y: ev.clientY });
        };

        window.addEventListener('mousemove', updateMousePosition);

        return () => {
            window.removeEventListener('mousemove', updateMousePosition);
        };
    }, []);

    return mousePosition;
};

const DragPreview = ({ draggingPiece, squareDimensions, game }) => {
    const mousePosition = useMousePosition()
    const draggingRef = useRef(null); // Ref for the element that follows the mouse

    const style = {
        position: 'fixed',
        left: `${mousePosition?.x}px`,
        top: `${mousePosition?.y}px`,
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'none',
        zIndex: 2000,
        cursor: 'grab',
    };

    if (!draggingPiece) {
        return null;
    }

    return (
        <div ref={draggingRef} style={style}>
            <ChessPiece contents={game?.board[draggingPiece]} dimensions={squareDimensions} location={draggingPiece} />
        </div>
    );
};

function Board({
    game,
    setGame,
    current,
    draggingPiece,
    setDraggingPiece,
    selectedPiece,
    setSelectedPiece,
    orientation,
    moveSound,
    captureSound,
    flashHandicap,
    volume,
    playersInCheck,
    setPlayersInCheck,
    neverPremoveIntoCheck,
    color,
    showError,
    showHighlights,
    squareRefs,
    username,
    port,
    smallScreen,
    alwaysPromoteToQueen,
    maxPlySeen,
    castleViaRook,
    haveSeenOpponentDrawback,
    isFogOfWar
}) {
    const [squareHighlights, setSquareHighlights] = useState({});
    const [arrows, setArrows] = useState([]);
    const [drawingArrowStartSquare, setDrawingArrowStartSquare] = useState(null);
    const [drawingArrowEndSquare, setDrawingArrowEndSquare] = useState(null);
    const [promotionSquare, setPromotionSquare] = useState(null);
    const [promotionStart, setPromotionStart] = useState(null);

    const duckSquare = game?.handicaps?.[color]?.includes('Untitled Duck Drawback') && game?.handicaps?.[color]?.match(/[A-Ha-h][1-8]/)?.[0]?.toUpperCase();
    const gardenSquares = game?.handicaps?.[color]?.includes('Secret Garden') && game?.messages?.[color]?.match(/[A-Ha-h][1-8]/g)?.map(square => square?.toUpperCase()) || [];
    const sunSquare = game?.handicaps?.[color]?.includes('Blinded by the Sun') && game?.handicaps?.[color]?.match(/[A-Ha-h][1-8]/)?.[0]?.toUpperCase();

    const currentHighlight = drawingArrowStartSquare === drawingArrowEndSquare ? drawingArrowStartSquare : null;

    let squareDimensions = smallScreen ? 'min(12vw, 9vh)' : 'min(7vw, 10vh, 200px)'
    let triangleDimensions = smallScreen ? 'min(1vw, 0.81vh)' : 'min(1.4vw, 1vh, 20px)'

    const arrowWidth = window.innerWidth / 100;

    const extendedArrows = (
        drawingArrowStartSquare && drawingArrowEndSquare && drawingArrowStartSquare !== drawingArrowEndSquare ?
            [...arrows, { start: drawingArrowStartSquare, end: drawingArrowEndSquare }] : arrows
    );

    const getSquarePosition = (key) => {
        const squareRef = squareRefs?.current?.[key]?.current;

        if (squareRef) {
            const rect = squareRef.getBoundingClientRect();
            return {
                x: rect.left + rect.width / 2 + window.scrollX,
                y: rect.top + rect.height / 2 + window.scrollY,
            };
        }
        return null;
    };

    const arrowsPos = extendedArrows.map((arrow) => {
        return {
            start: arrow.start && getSquarePosition(arrow.start),
            end: arrow.end && getSquarePosition(arrow.end),
        }
    });

    function display(name) {
        let ret = ''
        if (smallScreen) {
            return ret
        }
        if (name[1] === (color === 'white' ? '1' : '8')) {
            ret += 'file'
        } if (name[0] === (color === 'white' ? 'H' : 'A')) {
            ret += 'rank';
        }
        return ret;
    }

    function Arrow({ startX, startY, endX, endY, strokeWidth }) {
        const dx = endX - startX;
        const dy = endY - startY;
        const angle = Math.atan2(dy, dx) * 180 / Math.PI;

        return (
            <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}>
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="1.9" refY="1.9" orient="auto">
                        <polygon points="0 0.3, 3 1.85, 0 3.5" fill="green" />
                    </marker>
                </defs>
                <line x1={startX} y1={startY} x2={endX} y2={endY} stroke="green" strokeWidth={strokeWidth} markerEnd="url(#arrowhead)" opacity="0.7" />
            </svg>
        );
    }

    const clearArrowsAndHighlights = () => {
        if (arrows.length !== 0) {
            console.log('arrows, ', arrows)
            setArrows([]);
        }
        if (Object.keys(squareHighlights).length != 0) {
            setSquareHighlights({});
        }
        if (drawingArrowStartSquare) {
            setDrawingArrowStartSquare(null);
        }
        if (drawingArrowEndSquare) {
            setDrawingArrowEndSquare(null);
        }
    }

    useEffect(() => {
        if (!!selectedPiece) {
            clearArrowsAndHighlights();
        }
    }, [selectedPiece])
 
    useEffect(() => {
        if (current) {
            setSelectedPiece(null);
        }
    }, [current])

    const onContextMenu = (e) => {
        e.preventDefault();
    }

    function cancelPremove() {
        if (!game?.premoves?.[color]) {
            return false;
        }
        let newGame = { ...game };
        if (newGame?.premoves?.[color]) {
            newGame.premoves[color] = null;
        }
        setGame(newGame);
        fetchWrapper('/premove/cancel', { id: game.id, color, username }, 'POST', port)
            .then((response) => {
                if (response.success) {
                    setGame(response.game);
                }
                else {
                    showError(response.error);
                }
            })
        return true;
    }

    const handleMouseDown = (e, key) => {
        if (e.button === 2) {
            if (draggingPiece) {
                setDraggingPiece(null);
                return
            } if (selectedPiece) {
                setSelectedPiece(null);
                return
            }
            if (!cancelPremove()) {
                setDrawingArrowStartSquare(key);
            }
        }
    };

    const handleMouseMove = (e, key) => {
        if (drawingArrowStartSquare) {
            setDrawingArrowEndSquare(key)
        }
    };

    const handleMouseUp = (e, key) => {
        if (!drawingArrowStartSquare) {
            return
        }
        if (drawingArrowStartSquare === key) {
            setSquareHighlights({ ...squareHighlights, [key]: !squareHighlights[key] });
        }
        else {
            const newArrow = { start: drawingArrowStartSquare, end: drawingArrowEndSquare };

            let newArrowIsInArrows = false;

            arrows.forEach((arrow) => {
                if (arrow.start === newArrow.start && arrow.end === newArrow.end) {
                    newArrowIsInArrows = true;
                }
            });

            if (newArrowIsInArrows) {
                setArrows(arrows.filter((arrow) => arrow.start !== newArrow.start || arrow.end !== newArrow.end));
            } else {
                setArrows([...arrows, newArrow]);
            }
        }
        if (drawingArrowStartSquare) {
            setDrawingArrowStartSquare(null);
        }
        if (drawingArrowEndSquare) {
            setDrawingArrowEndSquare(null);
        }
    };

    return (
        <div className="board" onContextMenu={onContextMenu}>
            {boardOrder(orientation).map((key) => (
                <div key={key} onClick={clearArrowsAndHighlights} onMouseDown={(e) => handleMouseDown(e, key)} onMouseMove={(e) => handleMouseMove(e, key)} onMouseUp={(e) => handleMouseUp(e, key)}>
                    <Square
                        key={key}
                        squareRef={squareRefs.current[key]}
                        port={port}
                        color={color}
                        game={game}
                        setGame={setGame}
                        dimensions={squareDimensions}
                        triangleDimensions={triangleDimensions}
                        name={key}
                        contents={game.board[key]}
                        selectedPiece={selectedPiece}
                        setSelectedPiece={setSelectedPiece}
                        draggingPiece={draggingPiece}
                        setDraggingPiece={setDraggingPiece}
                        showError={showError}
                        moveSound={moveSound}
                        captureSound={captureSound}
                        flashHandicap={flashHandicap}
                        volume={volume}
                        display={display(key)}
                        playersInCheck={playersInCheck}
                        setPlayersInCheck={setPlayersInCheck}
                        neverPremoveIntoCheck={neverPremoveIntoCheck}
                        alwaysPromoteToQueen={alwaysPromoteToQueen}
                        promotionSquare={promotionSquare}
                        setPromotionSquare={setPromotionSquare}
                        promotionStart={promotionStart}
                        setPromotionStart={setPromotionStart}
                        username={username}
                        highlightColor={game.result && game.ply < maxPlySeen.current ? game.ply % 2 === 0 ? 'black' : 'white' : color}
                        containsImage={duckSquare === key ? 'duck' : gardenSquares?.includes(key) ? 'flower' : sunSquare === key ? 'sun' : null}
                        highlighted={squareHighlights[key] || key === currentHighlight}
                        clearArrowsAndHighlights={clearArrowsAndHighlights}
                        castleViaRook={castleViaRook}
                        showHighlights={((game.ply % 2) == (color == 'white' ? 0 : 1) && game.result) ? (showHighlights && haveSeenOpponentDrawback) : showHighlights}
                        hidePieces={isFogOfWar}
                        cancelPremove={cancelPremove}
                    />
                </div>
            ))}
            <DragPreview draggingPiece={draggingPiece} game={game} squareDimensions={squareDimensions} />
            {arrowsPos && arrowsPos.map((arrowPos, index) => {
                return <Arrow
                    key={index}
                    startX={arrowPos.start?.x}
                    startY={arrowPos.start?.y}
                    endX={arrowPos.end?.x}
                    endY={arrowPos.end?.y}
                    strokeWidth={arrowWidth}
                />
            })}
        </div>
    )
}


export default function GamePage() {
    let { id, color } = useParams();
    let [error, setError] = useState(null);
    let [message, setMessage] = useState(null);
    let [game, setGameInner] = useState(null);
    // isOver makes it so the dialog doesn't open if you open a linked game that's already over
    let [isOver, setIsOver] = useState(true);
    let [haveSeenOpponentDrawback, setHaveSeenOpponentDrawback] = useState(false);
    let [loading, setLoading] = useState(true);
    let [gameError, setGameError] = useState(null);
    let [smallScreen, setSmallScreen] = useState(window.innerWidth < 1200);
    let [shortScreen, setShortScreen] = useState(window.innerHeight < 900);
    let [showHandicaps, setShowHandicaps] = useState(true);
    let [socket, setSocket] = useState(null);
    const [playersInCheck, setPlayersInCheck] = useState({ white: false, black: false });
    const [flash, setFlash] = useState(false);
    const [haveSeenSettingsDialog, setHaveSeenSettingsDialog] = useState(false);
    const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
    const [gameOverDialogOpen, setGameOverDialogOpen] = useState(false);
    const [rematchDeclinedDialogOpen, setRematchDeclinedDialogOpen] = useState(false);
    const [neverPremoveIntoCheck, setNeverPremoveIntoCheck] = useState(false);
    const [alwaysPromoteToQueen, setAlwaysPromoteToQueen] = useState(false);
    const [centerBoard, setCenterBoard] = useState(false);
    const [castleViaRook, setCastleViaRook] = useState(false);
    const [showHighlights, setShowHighlights] = useState(true);
    const [volume, setVolume] = useState(100);
    const [confirmResign, setConfirmResign] = useState(false);
    const [spectating, setSpectating] = useState(false);
    const [wasInGame, setWasInGame] = useState(false);
    const [maintenanceSoon, setMaintenanceSoon] = useState(false);
    const [maintenanceMessage, setMaintenanceMessage] = useState(null);
    const [lag, setLag] = useState(null);
    let [draggingPiece, setDraggingPiece] = useState(null);
    let [selectedPiece, setSelectedPiece] = useState(null);
    let [timeUntilAbort, setTimeUntilAbort] = useState(null);
    const [plyDict, setPlyDict] = useState({});

    const [ackedOpponentDrawback, setAckedOpponentDrawback] = useState(false);

    // Challenge stuff
    const [numFriendships, setNumFriendships] = useState(null);
    const [acceptChallengeDialogOpen, setAcceptChallengeDialogOpen] = useState(false);
    const [challengerDisplayName, setChallengerDisplayName] = useState(false);
    const [challengeDialogGameId, setChallengeDialogGameId] = useState(null);
    const [challengeDialogFriendshipId, setChallengeDialogFriendshipId] = useState(null);
    //

    let maxPlySeen = useRef(0);

    const [resizeCounter, setResizeCounter] = useState(0);

    const draggingContents = draggingPiece && game?.board?.[draggingPiece];

    useEffect(() => {
        if (draggingContents && draggingContents.color !== color) {
            setDraggingPiece(null);
        }
    }, [draggingContents, color]);

    useEffect(() => {
        if (game?.result) {
            setDraggingPiece(null);
        }
    }, [!!game?.result]);


    useEffect(() => {
        let now = new Date() / 1000;
        fetchWrapper('/now', {}, 'GET')
            .then((response) => {
                if (response.success) {
                    let latency = new Date() / 1000 - now;
                    let diff = response.now - new Date() / 1000 - (latency / 2);
                    if (!(-10 < diff && diff < 10)) {
                        showError("Your computer's time looks off from the server. You may experience issues with your clock. Please check your system time or go to time.is to see if there's a difference.")
                    }
                    setLag(diff);
                }
                else {
                    console.error(response.error);
                }
            });
    }, []);

    useEffect(() => {
        let interval = setInterval(() => {
            let now = new Date() / 1000;
            fetchWrapper('/now', {}, 'GET')
                .then((response) => {
                    if (response.success) {
                        let latency = new Date() / 1000 - now;
                        let diff = response.now - new Date() / 1000 - (latency / 2);
                        setLag(diff);
                    }
                    else {
                        console.error(response.error);
                    }
                });
        }, 10000);
        return () => clearInterval(interval);
    }, []);

    // Function to be called on window resize
    const handleEvent = () => {
        // The only point of this thing is to trigger a re-render, lol
        setResizeCounter(prevCounter => prevCounter + 1);
    };

    useEffect(() => {
        window.addEventListener('resize', handleEvent);
        window.addEventListener('scroll', handleEvent);

        return () => {
            window.removeEventListener('resize', handleEvent);
            window.removeEventListener('scroll', handleEvent);
        };
    }, []);

    useEffect(() => {
        fetchWrapper('/friendships', { username }, 'GET', port)
            .then((response) => {
                if (response.success) {
                    setNumFriendships(response?.friendships?.length);
                } else {
                    console.error(response.error);
                }
            });
    }, [])

    const squareRefs = useRef({
        'A1': createRef(),
        'A2': createRef(),
        'A3': createRef(),
        'A4': createRef(),
        'A5': createRef(),
        'A6': createRef(),
        'A7': createRef(),
        'A8': createRef(),
        'B1': createRef(),
        'B2': createRef(),
        'B3': createRef(),
        'B4': createRef(),
        'B5': createRef(),
        'B6': createRef(),
        'B7': createRef(),
        'B8': createRef(),
        'C1': createRef(),
        'C2': createRef(),
        'C3': createRef(),
        'C4': createRef(),
        'C5': createRef(),
        'C6': createRef(),
        'C7': createRef(),
        'C8': createRef(),
        'D1': createRef(),
        'D2': createRef(),
        'D3': createRef(),
        'D4': createRef(),
        'D5': createRef(),
        'D6': createRef(),
        'D7': createRef(),
        'D8': createRef(),
        'E1': createRef(),
        'E2': createRef(),
        'E3': createRef(),
        'E4': createRef(),
        'E5': createRef(),
        'E6': createRef(),
        'E7': createRef(),
        'E8': createRef(),
        'F1': createRef(),
        'F2': createRef(),
        'F3': createRef(),
        'F4': createRef(),
        'F5': createRef(),
        'F6': createRef(),
        'F7': createRef(),
        'F8': createRef(),
        'G1': createRef(),
        'G2': createRef(),
        'G3': createRef(),
        'G4': createRef(),
        'G5': createRef(),
        'G6': createRef(),
        'G7': createRef(),
        'G8': createRef(),
        'H1': createRef(),
        'H2': createRef(),
        'H3': createRef(),
        'H4': createRef(),
        'H5': createRef(),
        'H6': createRef(),
        'H7': createRef(),
        'H8': createRef(),
    });

    // useEffect(() => {
    //     const handleGlobalMouseDown = (event) => {
    //         if (event.button === 0) { // Left mouse down
    //             clearArrowsAndHighlights();
    //         }
    //     };

    //     document.addEventListener('mousedown', handleGlobalMouseDown);

    //     return () => {
    //         document.removeEventListener('mousedown', handleGlobalMouseDown);
    //     };
    // }, []);

    useEffect(() => {
        if (!(game?.current)) {
            setSelectedPiece(null);
            setDraggingPiece(null);
        }
    }, [!!game?.current]);

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

    useEffect(() => {
        const maintenanceSilenced = localStorage.getItem('maintenanceSoonSilenced');

        if (maintenanceSilenced) {
            const { silenced, expires } = JSON.parse(maintenanceSilenced);

            if (silenced && new Date().getTime() < expires) {
            } else {
                localStorage.removeItem('maintenanceSoonSilenced'); // Remove the item if it has expired
            }
        }
    }, []);

    const keyToRemove = (keys, ply) => {
        let maxDiff = 0;
        let ret = null;
        for (let key of keys) {
            let diff = ply - key;
            if (diff > maxDiff) {
                maxDiff = diff;
                ret = key;
            }
        }
        return ret;
    }

    const addGameToPlyDict = (game) => {
        if (game.temporary) {
            return
        }
        let ply = game.ply;
        if (Object.keys(plyDict).length > 100) {
            let k = keyToRemove(Object.keys(plyDict), ply);
            delete plyDict[k];
        }
        plyDict[ply] = { ...game, board: { ...game.board } };
    }

    let setGame = (newGame, ignorePlyCheck) => {
        addGameToPlyDict(newGame);
        if (ignorePlyCheck || newGame.maxPly >= maxPlySeen.current) {
            newGame.current = newGame.ply >= maxPlySeen.current;
            setGameInner(newGame);
            maxPlySeen.current = Math.max(newGame.maxPly, maxPlySeen.current);
        }
    }

    let setGameFromPlyDict = (ply) => {
        if (plyDict[ply]) {
            let dictGame = plyDict[ply];
            let current = ply >= maxPlySeen.current;
            let lastMove = { ...dictGame.lastMove, timestamp: game.lastMove?.timestamp };
            let timer = game.result ? { ...dictGame.timer, running: false } : game.timer;
            setGameInner({ ...game, moves: dictGame.moves, board: { ...dictGame.board }, ply: dictGame.ply, timer, lastMove, current, messages: dictGame.messages, playersInCheck: dictGame.playersInCheck, highlights: dictGame.highlights, materialIndicatorInformation: dictGame.materialIndicatorInformation });
            setPlayersInCheck(dictGame.playersInCheck);
        }
    }

    let port = getPort(id);

    if (localStorage.getItem('log')) {
        log('volume', volume);
    }

    // when the board.temporary is truth-y, alert if it not unset in 5s
    // if it gets unset, clear the timeout
    useEffect(() => {
        if (game?.temporary) {
            const timeout = setTimeout(() => {
                updateGame(game.id);
            }, 5000);
            return () => clearTimeout(timeout);
        }
    }, [game?.temporary]);


    useEffect(() => {
        if (socket) {
            socket.on('disconnect', () => {
                setSocket(null);
            });
        }

        return () => {
            if (socket) {
                socket.off('disconnect');
            }
        }
    }, [socket]);

    useEffect(() => {
        if (!socket) {
            log('making socket');
            if (process.env.REACT_APP_LOCAL) {
                console.log(process.env.REACT_APP_FULL_URL)
                setSocket(io.connect(process.env.REACT_APP_FULL_URL))
            } else {
                setSocket(io.connect(baseURL, { transports: ['websocket'], path: `/app${port - 5000}/socket.io` }));
            }
        }
    }, [socket, port]);

    // disconnect socket when unmounting
    useEffect(() => {
        return () => {
            log('disconnecting socket');
            socket && socket.disconnect();
        }
    }, [socket]);

    // Load the initial value from local storage when the component mounts
    useEffect(() => {
        const storedHaveSeenSettingsDialog = localStorage.getItem('haveSeenSettingsDialog');
        setHaveSeenSettingsDialog(storedHaveSeenSettingsDialog === 'true');
        const storedValue = localStorage.getItem('neverPremoveIntoCheck');
        setNeverPremoveIntoCheck(storedValue === 'true');
        const storedAlwaysPromoteToQueen = localStorage.getItem('alwaysPromoteToQueen');
        setAlwaysPromoteToQueen(storedAlwaysPromoteToQueen === 'true');
        const storedCenterBoard = localStorage.getItem('centerBoard');
        setCenterBoard(storedCenterBoard === 'true');
        const storedCastleViaRook = localStorage.getItem('castleViaRook');
        setCastleViaRook(storedCastleViaRook === 'true');
        const storedShowHighlights = localStorage.getItem('showHighlights');
        setShowHighlights(storedShowHighlights === null || storedShowHighlights === 'true');
    }, []);

    useEffect(() => {
        localStorage.setItem('neverPremoveIntoCheck', neverPremoveIntoCheck);
    }, [neverPremoveIntoCheck]);

    useEffect(() => {
        localStorage.setItem('alwaysPromoteToQueen', alwaysPromoteToQueen);
    }, [alwaysPromoteToQueen]);

    useEffect(() => {
        localStorage.setItem('centerBoard', centerBoard);
    }, [centerBoard]);

    useEffect(() => {
        localStorage.setItem('castleViaRook', castleViaRook);
    }, [castleViaRook]);


    useEffect(() => {
        localStorage.setItem('showHighlights', showHighlights);
    }, [showHighlights]);

    useEffect(() => {
        const storedValue = localStorage.getItem('volume');
        if ((storedValue !== null) && (storedValue !== undefined))
            setVolume(parseInt(storedValue));
    }, []);

    // Update the value in local storage whenever it changes
    useEffect(() => {
        localStorage.setItem('volume', volume);
    }, [volume]);

    let navigate = useNavigate();

    const gameRef = useRef(game);

    const flashHandicap = () => {
        setFlash(true);
        setTimeout(() => setFlash(false), 300);
        playWrongSound(wrongSound, volume);
    }

    const handleClickOpen = () => {
        setHaveSeenSettingsDialog(true);
        setSettingsDialogOpen(true);
    };

    useEffect(() => {
        localStorage.setItem('haveSeenSettingsDialog', haveSeenSettingsDialog);
    }, [haveSeenSettingsDialog]);

    const handleClose = () => {
        setSettingsDialogOpen(false);
    };

    useEffect(() => {
        game && playNotifySound(notifySound, volume);
    }, []);

    // flag that we've ever seen a non-result game so the dialog should open
    useEffect(() => {
        if (game && !game?.result) {
            setIsOver(false);
        }
    }, [game]);

    useEffect(() => {
        if (game?.result && !isOver) {
            setGameOverDialogOpen(true);
            playNotifySound(notifySound, volume);
            setSpectating(false);
        }
    }, [!!game?.result])

    useEffect(() => {
        const currentScoreSheet = getAllMovesFromScoresheet(gameRef.current?.scoreSheet || []);
        const newScoreSheet = getAllMovesFromScoresheet(game?.scoreSheet || []);

        const newScoreSheetKeys = Object.keys(game?.scoreSheet || {}).map((key) => parseInt(key));
        const latestNewScoreSheetMove = game?.scoreSheet[Math.max(...[...newScoreSheetKeys, 0])];

        const numNewMoves = newScoreSheet.length - currentScoreSheet.length;

        const isBlackMove = (latestNewScoreSheetMove?.length + numNewMoves) % 2 === 0;

        const isMyMove = (color === 'white' && !isBlackMove) || (color === 'black' && isBlackMove);

        if (isMyMove || game?.mostRecentMoveWasPremove) {

            // Play sounds for the last numNewMoves moves
            if (numNewMoves < 3) {
                for (let i = numNewMoves; i > 0; i--) {
                    const move = newScoreSheet[newScoreSheet.length - i];
                    const isCapture = move.includes('x');
                    playMoveSound(moveSound, captureSound, volume, isCapture);
                }
            }
        }

        if (isMyMove || game?.mostRecentMoveWasPremove) {
            // It gets set by submitMove when it's not your move
            setPlayersInCheck({ white: game?.playersInCheck?.['white'], black: game?.playersInCheck?.['black'] });
        }
        gameRef.current = game; // Update the ref whenever `game` changes
    }, [game]);

    // localStorage.getItem('log') && log(game);

    // let spectating = !(['white', 'black'].includes(color));
    // let spectating = ![game?.displayNames?.white, game?.displayNames?.black].includes(username);

    let username = getUsername(20);

    const showError = (message) => {
        if (message == 'Invalid move') return;
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

   function handleKeyDown(event) {
        if (event.key === 'Escape') {
            setSelectedPiece(null);
        }
    }

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, []);

    function updateGame(id) {
        fetchWrapper('/game', { id, color, username }, 'GET', port)
            .then((response) => {
                if (response.success) {
                    setGame(response.game);
                    if (!response?.game?.result) {
                        setSpectating(response.spectating);
                    }
                } else {
                    showError(response.error);
                }
            })
    }

    useEffect(() => {
        function ping() {
            if (!game) {
                return;
            }

            fetchWrapper('/ping', { id: game.id }, 'GET', port)
                .then((response) => {
                    if (response.success) {
                        if (localStorage.getItem('log')) {
                            console.log(response.maxPly, game.maxPly);
                        }
                        // The second clause below is a bandaid to make sure things update on Safari
                        if (response.maxPly > game.maxPly || (game.maxPly === 2 && game.ply === 1) || (response.result && !game.result)) {
                            console.log('updating game');
                            updateGame(game.id);
                        }
                    } else {
                        showError(response.error);
                    }
                })
        }

        let interval = setInterval(ping, process.env.REACT_APP_LOCAL ? 2000 : 5000);

        return () => clearInterval(interval);
    }, [!!game, game?.id, game?.maxPly, game?.result]);

    useEffect(() => {
        function handleResize() {
            setSmallScreen(window.innerWidth < 1200);
            setShortScreen(window.innerHeight < 900);
        }

        window.addEventListener('resize', handleResize);

        return () => window.removeEventListener('resize', handleResize);
    }, []);

    function draw() {
        fetchWrapper('/offer_draw', { id, color, username }, 'POST', port)
            .then((response) => {
                if (response.success) {
                    setGame(response.game);
                } else {
                    showError(response.error);
                }
            })
    }

    function resign() {
        fetchWrapper('/resign', { id, color, username }, 'POST', port)
            .then((response) => {
                if (response.success) {
                    setGame(response.game);
                } else {
                    showError(response.error);
                }
            })
    }

    function revealHandicap() {
        fetchWrapper('/reveal_drawback', { id, color, username }, 'POST', port)
            .then((response) => {
                if (response.success) {
                    setGame(response.game);
                } else {
                    showError(response.error);
                }
            })
    }

    function abort() {
        fetchWrapper('/abort', { id, color, username }, 'POST', port)
            .then((response) => {
                if (response.success) {
                    setGame(response.game);
                } else {
                    showError(response.error);
                }
            })
    }

    useEffect(() => {
        fetchWrapper('/game', { id, color, username }, 'GET', port)
            .then((response) => {
                if (response.success) {
                    if (response.game.result) {
                        fetchWrapper('/game', { id, color, username, ply: 2 }, 'GET', port)
                            .then((response) => {
                                if (response.success) {
                                    setGame(response.game);
                                } else {
                                    showError(response.error);
                                }
                            })
                    } else {
                        setGame(response.game);
                        setSpectating(response.spectating);
                        setWasInGame(response.spectating);
                    }
                    setLoading(false);
                } else {
                    setGameError(response.error);
                    setLoading(false);
                }
            })
    }, []);

    useEffect(() => {
        socket && socket.emit('join', { room: id + '-' + username });
        socket && socket.emit('join', { room: id })

        return () => {
            socket && socket.emit('leave', { room: id + '-' + username })
            socket && socket.emit('leave', { room: id })
        }
    }, [socket])

    useEffect(() => {
        if (!socket) {
            log('no socket yet')
            return;
        }

        log('adding socket callbacks')

        socket.on('update', (data) => {
            setGame({
                ...data['game'],
                mostRecentMoveWasPremove: data['isPremove'],
            });
            if (data['premoveFailedBecauseOfHandicap']) {
                const lastMoveWasWhite = data['game'].ply % 2 === 0;
                if (lastMoveWasWhite && color === 'black' || !lastMoveWasWhite && color === 'white') {
                    flashHandicap();
                }
            }
        }
        );

        socket.on('message', (data) => {
            showMessage(data['message']);
        });

        socket.on('other_message', (data) => {
            if (data['message'] == 'decline_rematch') {
                setRematchDeclinedDialogOpen(true);
            }
        });

        socket.on('rematch', (data) => {
            setTimeout(() => {
                showMessage('Your opponent would like to rematch!')
            }, 1000);
        });

        socket.on('new_player', (data) => {
            if (data['color'] == color) {
                return;
            }
            fetchWrapper('/game', { id, username, color }, 'GET', port)
                .then((response) => {
                    if (response.success) {
                        setGame(response.game);
                    } else {
                        showError(response.error);
                    }
                })
        });

        return () => {
            if (!socket) {
                return
            }
            socket.off('update');
            socket.off('other_message');
            socket.off('rematch');
            socket.off('new_player');
        }
    }, [socket]);

    useEffect(() => {
        const handleMouseUp = () => {
            setDraggingPiece(null);
        }

        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, []);

    let boardDimensions = smallScreen ? 'min(96vw, 72vh)' : 'min(56vw, 80vh, 1600px)'
    const shortGameScore = getAllMovesFromScoresheet(game?.scoreSheet || [])?.length < 2;
    const isFogOfWar = game?.handicaps?.[color]?.includes('Fog of War') && !game?.result;
    const challengeable = (game?.result || shortGameScore) && numFriendships > 0;

    useEffect(() => {
        // Define the function that makes the backend call
        const pollBackend = async () => {
            try {
                fetchWrapper('/poll_for_challenge', { username }, 'GET', port)
                    .then((response) => {
                        if (response.success && response.challengerDisplayName) {
                            setAcceptChallengeDialogOpen(true);
                            setChallengerDisplayName(response.challengerDisplayName);
                            setChallengeDialogGameId(response.gameId);
                            setChallengeDialogFriendshipId(response.friendshipId);
                        } else if (!response.success) {
                            showError(response.error);
                        }
                    })
            } catch (error) {
                console.error('Error polling backend:', error);
            }
        };

        let intervalId;
        if (challengeable) {
            intervalId = setInterval(pollBackend, 5000);
        }

        // Cleanup function to stop the polling
        return () => {
            if (intervalId) {
                clearInterval(intervalId);
            }
        };
    }, [challengeable]); // Rerun the effect when `challengeable` changes    

    let abortTimer = game?.abortTimer;

    useEffect(() => {
        if (abortTimer) {
            let interval = setInterval(() => {
                let now = new Date() / 1000;
                let diff = new Date(abortTimer) - now;
                if (game.turn === color) {
                    setTimeUntilAbort(Math.max(0, diff - (lag || 0)));
                }
            }, 1000);
            return () => clearInterval(interval);
        }
    }, [abortTimer]);
    
    function Result({ game, color }) {
        if (!game || !game.result) {
            return null;
        }

        let result = game.result;

        let won = result === `${color} wins` || result === `${color} wins on time`;

        let lost = result === `${color === 'white' ? 'black' : 'white'} wins` || result === `${color === 'white' ? 'black' : 'white'} wins on time`;


        let style = {
            color: won ? 'green' : lost ? 'red' : 'white',
            marginLeft: '10px',
        }

        return (
            <div style={style}>
                <h1> {result} </h1>
            </div>
        )
    }

    let contentsOfSelectedPiece = selectedPiece && game.board?.[selectedPiece];

    useEffect(() => {
        if (!contentsOfSelectedPiece || contentsOfSelectedPiece?.color !== color) {
            setSelectedPiece(null);
        }
    }, [contentsOfSelectedPiece, color])

    if (loading) {
        return (
            <div className="container">
                <h1>Loading...</h1>
            </div>
        )
    }

    if (gameError || !game) {
        return (
            <div className="container">
                <h1>{gameError || 'Loading...'}</h1>
            </div>
        )
    }

    let buttonStyles = {
        padding: '10px',
        borderRadius: '5px',
        cursor: 'pointer',
        marginBottom: '5px',
        marginLeft: '10px',
    }

    let yourHandicap = game.handicaps?.[color];

    let opponent_offered_draw = game.drawOffer && game.drawOffer !== color;

    let you_offered_draw = game.drawOffer && game.drawOffer === color;

    let outerContainer = smallScreen ? 'vertical-container' : 'horizontal-container';

    let innerContainer = smallScreen ? 'horizontal-container' : 'vertical-container';

    function SpectatorHandicapInfo() {
        return (
            <div className="handicap-info">
                <h3> White Handicap </h3>
                <div className="handicap">
                    {game.handicaps?.['white']}
                </div>
                <div className="message">
                    <div className="message-text" style={{ opacity: game.messages?.['white'] ? 1 : 0 }}>
                        {game.messages?.['white'] || 'placeholder'}
                    </div>
                </div>
                <h3> Black Handicap </h3>
                <div className="handicap">
                    {game.handicaps?.['black']}
                </div>
                <div className="message">
                    <div className="message-text" style={{ opacity: game.messages?.['black'] ? 1 : 0 }}>
                        {game.messages?.[color] || 'placeholder'}
                    </div>
                </div>
                <div className="message">
                    <div className="message-text" style={{ opacity: game.messages?.['all'] ? 1 : 0 }}>
                        {game.messages?.['all'] || 'placeholder'}
                    </div>
                </div>
            </div>
        )
    }

    function HandicapInfo({ maxWidth, smallScreen, spectating, showHandicap, setShowHandicap }) {
        const containerStyle = maxWidth ? { maxWidth: maxWidth, marginLeft: smallScreen ? '0px' : '50px', fontSize: smallScreen ? '16px' : '24px', ...(smallScreen ? {} : {}) } : {};

        let haveRevealedDrawback = game?.revealedHandicaps?.[color];

        return (
            <div className="handicap-info" style={containerStyle}>
                {spectating && <h1 style={{ color: 'pink' }}> You are spectating </h1>}
                {!spectating && showHandicap && <div className={`handicap ${flash ? 'flash' : ''}`} >
                    <EnrichedText wordTooltips={WORD_TOOLTIPS}>
                        {yourHandicap}
                    </EnrichedText>
                </div>}
                {showHandicap && <div className="message" style={{ minHeight: smallScreen ? '40px' : '120px' }}>
                    {game.messages?.[color] + game.messages?.['all'] + (game.result ? game.messages?.[color === 'white' ? 'black' : 'white'] : '') ?
                        <>
                            <div className="message-text">
                                {game.result && game.ply < maxPlySeen.current && haveSeenOpponentDrawback ?
                                    <div>
                                        {game.messages?.[color] && <div> Your message: {game.messages?.[color]} </div>}
                                        {game.messages?.[color === 'white' ? 'black' : 'white'] && <div> Their message: {game.messages?.[color === 'white' ? 'black' : 'white']} </div>}
                                    </div> :
                                    <div style={{ opacity: game.messages?.[color] ? 1 : 0 }}> {game.messages?.[color]} </div>}
                            </div>
                            <div className="message-text">
                                {game.messages?.['all']}
                            </div>
                        </> :
                        <div className="message-text" style={{ opacity: 0 }}> placeholder </div>}
                </div>}
                {game?.revealedHandicaps?.[color === 'white' ? 'black' : 'white'] && !ackedOpponentDrawback && <div> <Typography style={{ color: 'red' }}>
                    Your opponent revealed their drawback: {game?.revealedHandicaps?.[color === 'white' ? 'black' : 'white']}
                </Typography>
                    <Button style={buttonStyles} variant="contained" onClick={() => setAckedOpponentDrawback(true)}>Dismiss</Button>
                </div>}
                {!smallScreen && <>
                    <br />
                    <Button variant="contained" style={buttonStyles} onClick={() => setShowHandicap(!showHandicap)} styles={{ marginTop: '10px' }}>
                        {showHandicap ? 'Hide Drawback' : 'Show Drawback'}
                    </Button>
                </>}
                {!game.result && !smallScreen && <Button disabled={haveRevealedDrawback} style={buttonStyles} variant="contained" onClick={revealHandicap}>Reveal Drawback To Opponent</Button>}
            </div>
        )
    }

    function SpectatorButtons() {
        return (
            <div className="vertical-container" style={{ marginTop: smallScreen ? '20px' : '70px', alignItems: smallScreen ? 'center' : 'flex-start', width: '100%' }}>
                <Result game={game} color={color} />
                <Button style={buttonStyles} variant="contained" onClick={() => navigate('/')}>Back</Button>
                <Button style={buttonStyles} variant="contained" onClick={() => setShowHandicaps(!showHandicaps)}>
                    {showHandicaps ? 'Hide Handicaps' : 'Show Handicaps'}
                </Button>
                {showHandicaps && <SpectatorHandicapInfo />}
            </div>
        )
    }

    function Buttons() {       
        let abortButtonText = timeUntilAbort !== null && game.turn === color && timeUntilAbort < 15 ? `Auto-abort in ${timeUntilAbort.toFixed(0)}` : 'Abort';
        
        return (
            <div className="vertical-container" style={{ marginTop: smallScreen ? '20px' : '40px', alignItems: smallScreen ? 'center' : 'flex-start', ...(smallScreen ? {} : { marginLeft: '40px' }) }}>
                {/* <Result game={game} color={color} /> */}
                <div className="horizontal-container" style={{ alignItems: smallScreen ? 'center' : 'flex-start', ...(smallScreen ? { maxWidth: '100%' } : {}) }}>
                    {/* <Button style={buttonStyles} variant="contained" onClick={() => navigate('/')}>Back</Button> */}
                    {!game.result ? <Button disabled={!!game.result || you_offered_draw} style={opponent_offered_draw ? { ...buttonStyles, backgroundColor: 'pink' } : buttonStyles} variant="contained" onClick={draw}>
                        {you_offered_draw ? 'Draw Offered' : opponent_offered_draw ? 'Accept Draw' : 'Offer Draw'}
                    </Button> : <Button variant="contained" onClick={() => onRematch(game?.id, navigate, showError, username, handleClose)}>
                        {smallScreen ? <Typography style={{ fontSize: '12px' }}>
                            Rematch
                        </Typography> : 'Rematch'}
                    </Button>}
                    {!game.result ? (
                        shortGameScore ? <Button disabled={!!game.result} style={{...buttonStyles, ...(abortButtonText === 'Abort' ? {} : { backgroundColor: 'pink'})}} variant="contained" onClick={abort}>{abortButtonText}</Button> :
                            confirmResign ? <Button disabled={!!game.result} style={buttonStyles} variant="contained" onClick={resign}>Confirm Resign</Button>
                                : <Button disabled={!!game.result} style={buttonStyles} variant="contained" onClick={() => setConfirmResign(true)}>Resign</Button>)
                        : <Button variant="contained" onClick={() => onBackToLobby(game?.rematchGameId, navigate)}>Back to lobby</Button>}
                    {/* <Button style={buttonStyles} variant="contained" onClick={() => setDisplayPromotion(!displayPromotion)}>
                        {displayPromotion ? 'Hide Promotion Options' : 'Show Promotion Options'}
                    </Button> */}
                    {!game.result && <CopyButton showMessage={showMessage} showError={showError} buttonStyles={buttonStyles} game={game} color={color} />}
                    {game.result && <Button style={{ backgroundColor: 'green', color: 'white' }} variant="contained" onClick={() => setGameOverDialogOpen(true)}>View info</Button>}
                    {game.result && <CopyButton isShareLinkButton showMessage={showMessage} showError={showError} buttonStyles={buttonStyles} game={game} color={color} />}
                    {smallScreen && !game.result && <Button disabled={game?.revealedHandicaps?.[color]} style={{ ...buttonStyles, minHeight: '45px', fontSize: '9px' }} variant="contained" onClick={revealHandicap}>Reveal Drawback To Opponent</Button>} 
                    {smallScreen && <IconButton variant="outlined" onClick={handleClickOpen}>
                        <SettingsIcon style={{ color: 'white' }} />
                    </IconButton>}
                </div>
            </div>
        )
    }

    return (
        <div>
            <div style={{ opacity: 0, width: '1px', height: '1px', overflow: 'hidden' }}>
                <img src={`${process.env.PUBLIC_URL}/assets/white-king-in-check.png`} alt="Preload white king in check" />
                <img src={`${process.env.PUBLIC_URL}/assets/black-king-in-check.png`} alt="Preload black king in check" />
            </div>
            {!smallScreen && <div style={{ position: 'absolute', top: 10, right: 10, padding: '10px' }}>
                <IconButton variant="outlined" onClick={handleClickOpen}>
                    <SettingsIcon style={{ color: haveSeenSettingsDialog ? 'white' : 'red' }} />
                </IconButton>
            </div>}
            <div style={{ width: '100%', display: 'flex', justifyContent: 'center', position: 'fixed', left: 0, top: 10 }}>
                {error && <Toast message={error} onClose={() => setError(null)} />}
                {message && <Toast message={message} onClose={() => setMessage(null)} isError={false} />}
            </div>
            {maintenanceSoon && <div style={{ width: '100%', display: 'flex', justifyContent: 'center', position: 'fixed', left: 0, top: 40 }}>
                <Toast message={maintenanceMessage || "We will be restarting our servers and rolling out new features and fixes over the course of the next hour. You may experience frequent interruptions."} isError={true} onClose={handleCloseMaintenanceToast} />
            </div>}
            {lag && Math.abs(lag) > 4 &&
                <div style={{ position: 'absolute', top: 10, left: 10, padding: '10px', zIndex: -1 }}
                    title="This message appears when there is a mismatch between your computer time and the server time. We will attempt to offset your timers the appropriate amount but you may find it feels inconsistent or off. Consider syncing your system time.">
                    <h1 style={{ fontSize: '12px', color: Math.abs(lag) > 1 ? 'red' : 'white' }}> Server time mismatch (seconds): {lag.toFixed(1)} </h1>
                </div>
            }
            <div className={outerContainer} style={{ justifyContent: centerBoard ? 'center' : 'flex-start', alignItems: smallScreen ? 'flex-start' : 'center', alignItems: 'center', ...(smallScreen ? {} : { minHeight: '800px' }) }}>
                <div className="vertical-container" style={{ marginLeft: smallScreen ? '0px' : '20px', marginTop: smallScreen ? '0px' : '50px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', flexDirection: 'column', width: boardDimensions }}>
                            {smallScreen && <HandicapInfo smallScreen={smallScreen} spectating={spectating} showHandicap={showHandicaps} setShowHandicap={setShowHandicaps} />}
                            <div style={{ display: 'flex', justifyContent: 'space-between', flexDirection: 'row', width: '100%', minHeight: '45px' }}>
                                {game && game.materialIndicatorInformation && window.innerWidth > 450 && !isFogOfWar && <MaterialIndicator
                                    color={color === 'white' ? 'black' : 'white'}
                                    materialIndicatorInfo={game.materialIndicatorInformation}
                                />}
                                {game && game.timer && <Timer
                                    game={game}
                                    setGame={setGame}
                                    color={color === 'white' ? 'black' : 'white'}
                                    lowTimeSound={lowTimeSound}
                                    volume={volume}
                                    playLowTimeSound={playLowTimeSound}
                                    lag={lag}
                                />}
                            </div>
                            <Board
                                game={game}
                                setGame={setGame}
                                draggingPiece={draggingPiece}
                                setDraggingPiece={setDraggingPiece}
                                selectedPiece={selectedPiece}
                                setSelectedPiece={setSelectedPiece}
                                orientation={color}
                                moveSound={moveSound}
                                captureSound={captureSound}
                                flashHandicap={flashHandicap}
                                volume={volume}
                                playersInCheck={playersInCheck}
                                setPlayersInCheck={setPlayersInCheck}
                                neverPremoveIntoCheck={neverPremoveIntoCheck}
                                showError={showError}
                                color={color}
                                squareRefs={squareRefs}
                                username={username}
                                smallScreen={smallScreen}
                                castleViaRook={castleViaRook}
                                alwaysPromoteToQueen={alwaysPromoteToQueen}
                                isFogOfWar={isFogOfWar}
                                maxPlySeen={maxPlySeen}
                                port={port}
                                showHighlights={showHighlights}
                                haveSeenOpponentDrawback={haveSeenOpponentDrawback}
                                current={game.current}
                            />
                            <div style={{ display: 'flex', justifyContent: 'space-between', flexDirection: 'row', width: '100%', minHeight: '55px' }}>
                                {game && game.materialIndicatorInformation && window.innerWidth > 450 && !isFogOfWar && <MaterialIndicator
                                    color={color}
                                    materialIndicatorInfo={game.materialIndicatorInformation}
                                />}
                                {game && game.timer && <Timer
                                    game={game}
                                    setGame={setGame}
                                    color={color}
                                    lowTimeSound={lowTimeSound}
                                    volume={volume}
                                    playLowTimeSound={playLowTimeSound}
                                    lag={lag}
                                    myTimer
                                />}
                            </div>
                            {smallScreen && !isFogOfWar && <div style={{ marginTop: '5px', alignSelf: 'center' }}> 
                                <ScoreSheet
                                    game={game}
                                    color={color}
                                    setGame={(game) => setGame(game, true)}
                                    setGameFromPlyDict={setGameFromPlyDict}
                                    setLoading={setLoading}
                                    showError={showError}
                                    moveSound={moveSound}
                                    captureSound={captureSound}
                                    volume={volume}
                                    username={username}
                                    setPlayersInCheck={setPlayersInCheck}
                                    smallScreen={smallScreen}
                                    shortScreen={shortScreen}
                                    plyDict={plyDict}
                                    justArrows={true}
                                />
                            </div>}
 
                            {!smallScreen ? null : spectating ? <SpectatorButtons /> : <Buttons />}
                       </div>
                        {!smallScreen && <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', marginLeft: '20px' }}>
                            {spectating ? <SpectatorButtons /> : <Buttons />}
                            <HandicapInfo maxWidth={'400px'} spectating={spectating} setShowHandicap={setShowHandicaps} showHandicap={showHandicaps} />
                            {!isFogOfWar && <div style={{ overflowX: 'hidden', marginTop: '20px' }}>
                                <ScoreSheet
                                    game={game}
                                    color={color}
                                    setGame={(game) => setGame(game, true)}
                                    setLoading={setLoading}
                                    showError={showError}
                                    moveSound={moveSound}
                                    captureSound={captureSound}
                                    volume={volume}
                                    username={username}
                                    setPlayersInCheck={setPlayersInCheck}
                                    smallScreen={smallScreen}
                                    shortScreen={shortScreen}
                                    plyDict={plyDict}
                                    setGameFromPlyDict={setGameFromPlyDict}
                                />
                            </div>}
                        </div>}
                    </div>
                    {smallScreen && !isFogOfWar && <div style={{ marginTop: '10px' }}> 
                        <ScoreSheet 
                            game={game} 
                            color={color} 
                            setGame={(game) => setGame(game, true)} 
                            setGameFromPlyDict={setGameFromPlyDict} 
                            setLoading={setLoading} 
                            showError={showError} 
                            moveSound={moveSound} 
                            captureSound={captureSound} 
                            volume={volume} 
                            username={username} 
                            setPlayersInCheck={setPlayersInCheck} 
                            smallScreen={smallScreen} 
                            shortScreen={shortScreen} 
                            plyDict={plyDict} 
                            hideArrows={true}
                        /> 
                    </div>}
                </div>
                {/* {spectating ? <SpectatorButtons /> : <Buttons />} */}
            </div>
            <SettingsDialog
                open={settingsDialogOpen}
                handleClose={handleClose}
                neverPremoveIntoCheck={neverPremoveIntoCheck}
                setNeverPremoveIntoCheck={setNeverPremoveIntoCheck}
                alwaysPromoteToQueen={alwaysPromoteToQueen}
                setAlwaysPromoteToQueen={setAlwaysPromoteToQueen}
                centerBoard={centerBoard}
                setCenterBoard={setCenterBoard}
                volume={volume}
                setVolume={setVolume}
                castleViaRook={castleViaRook}
                setCastleViaRook={setCastleViaRook}
                showHighlights={showHighlights}
                setShowHighlights={setShowHighlights}
            />
            <GameOverDialog
                open={gameOverDialogOpen}
                handleClose={() => setGameOverDialogOpen(false)}
                result={game?.result}
                color={color}
                allKingsExist={game?.allKingsExist}
                kingWasCapturedEnPassant={game?.kingWasCapturedEnPassant}
                handicaps={game?.handicaps}
                handicapElos={game?.handicapElos}
                handicapEloAdjustments={game?.handicapEloAdjustments}
                gameId={game?.id}
                rematchGameId={game?.rematchGameId}
                showError={showError}
                showMessage={showMessage}
                username={username}
                showRejoinQueue={game.displayNames.white != 'John Chess' && game.displayNames.black != 'John Chess' && !isOver}
                spectating={spectating && !wasInGame}
                smallScreen={smallScreen}
                port={port}
                haveSeenOpponentDrawback={haveSeenOpponentDrawback}
                setHaveSeenOpponentDrawback={setHaveSeenOpponentDrawback}
            />
            <RematchDeclinedDialog
                open={rematchDeclinedDialogOpen}
                handleClose={() => setRematchDeclinedDialogOpen(false)}
                rematchGameId={game?.rematchGameId}
            />
            {acceptChallengeDialogOpen && <AcceptChallengeDialog
                open={acceptChallengeDialogOpen}
                handleClose={() => setAcceptChallengeDialogOpen(false)}
                gameId={challengeDialogGameId}
                friendshipId={challengeDialogFriendshipId}
                challengerDisplayName={challengerDisplayName}
                username={username}
                fromPolling
                abortCurrentGame={abort}
                notifySound={notifySound}
            />}
        </div>
    )
}