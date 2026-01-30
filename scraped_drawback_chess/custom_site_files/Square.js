import React, { useEffect, useState } from 'react';
import ChessPiece from './ChessPiece';
import { fetchWrapper } from './Helpers';
import { playMoveSound, playWrongSound } from './Helpers';

let file_to_index = {
    'A': 0,
    'B': 1,
    'C': 2,
    'D': 3,
    'E': 4,
    'F': 5,
    'G': 6,
    'H': 7
}

let index_to_file = {
    0: 'A',
    1: 'B',
    2: 'C',
    3: 'D',
    4: 'E',
    5: 'F',
    6: 'G',
    7: 'H'
}

function nullify(value, set) {
    if (value !== null) {
        set(null);
    }
}

function pawnPremoves(name, color) {
    let ret = []
    let mult = color === 'white' ? 1 : -1;
    ret.push(name[0] + (parseInt(name[1]) + mult).toString());
    if (name[1] === '2' || name[1] === '7') {
        ret.push(name[0] + (parseInt(name[1]) + 2).toString());
    }
    ret.push(index_to_file[file_to_index[name[0]] - 1] + (parseInt(name[1]) + mult).toString());
    ret.push(index_to_file[file_to_index[name[0]] + 1] + (parseInt(name[1]) + mult).toString());
    return ret;
}

function knightPremoves(name) {
    let ret = []
    ret.push(index_to_file[file_to_index[name[0]] - 1] + (parseInt(name[1]) + 2).toString());
    ret.push(index_to_file[file_to_index[name[0]] + 1] + (parseInt(name[1]) + 2).toString());
    ret.push(index_to_file[file_to_index[name[0]] - 2] + (parseInt(name[1]) + 1).toString());
    ret.push(index_to_file[file_to_index[name[0]] + 2] + (parseInt(name[1]) + 1).toString());
    ret.push(index_to_file[file_to_index[name[0]] - 2] + (parseInt(name[1]) - 1).toString());
    ret.push(index_to_file[file_to_index[name[0]] + 2] + (parseInt(name[1]) - 1).toString());
    ret.push(index_to_file[file_to_index[name[0]] - 1] + (parseInt(name[1]) - 2).toString());
    ret.push(index_to_file[file_to_index[name[0]] + 1] + (parseInt(name[1]) - 2).toString());
    return ret;
}

function bishopPremoves(name) {
    let ret = []
    let mults = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
    for (let i = 0; i < mults.length; i++) {
        let mult = mults[i];
        let x = file_to_index[name[0]];
        let y = parseInt(name[1]);
        while (x >= 0 && x <= 7 && y >= 1 && y <= 8) {
            x += mult[0];
            y += mult[1];
            ret.push(index_to_file[x] + y.toString());
        }
    }
    return ret;
}

function rookPremoves(name) {
    let ret = []
    let mults = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    for (let i = 0; i < mults.length; i++) {
        let mult = mults[i];
        let x = file_to_index[name[0]];
        let y = parseInt(name[1]);
        while (x >= 0 && x <= 7 && y >= 1 && y <= 8) {
            x += mult[0];
            y += mult[1];
            ret.push(index_to_file[x] + y.toString());
        }
    }
    return ret;
}

function queenPremoves(name) {
    return bishopPremoves(name).concat(rookPremoves(name));
}

function kingPremoves(name, color) {
    let ret = []
    let mults = [[1, 1], [1, -1], [-1, 1], [-1, -1], [1, 0], [-1, 0], [0, 1], [0, -1]];
    for (let i = 0; i < mults.length; i++) {
        let mult = mults[i];
        let x = file_to_index[name[0]];
        let y = parseInt(name[1]);
        x += mult[0];
        y += mult[1];
        if (x >= 0 && x <= 7 && y >= 1 && y <= 8) {
            ret.push(index_to_file[x] + y.toString());
        }
    }
    return ret;
}

function makeLegalPremovesInner(name, piece, color) {
    if (piece === 'pawn') {
        return pawnPremoves(name, color);
    }
    if (piece === 'knight') {
        return knightPremoves(name);
    }
    if (piece === 'bishop') {
        return bishopPremoves(name);
    }
    if (piece === 'rook') {
        return rookPremoves(name);
    }
    if (piece === 'queen') {
        return queenPremoves(name);
    }
    if (piece === 'king') {
        return kingPremoves(name, color);
    }
}

function makeLegalPremoves(name, piece, color) {
    return makeLegalPremovesInner(name, piece, color).map((x) => ({ stop: x }));
}

export default function Square({
    port,
    squareRef,
    game,
    setGame,
    color,
    name,
    contents,
    dimensions,
    selectedPiece,
    setSelectedPiece,
    draggingPiece,
    setDraggingPiece,
    showError,
    triangleDimensions,
    moveSound,
    captureSound,
    flashHandicap,
    volume,
    display,
    playersInCheck,
    setPlayersInCheck,
    neverPremoveIntoCheck,
    alwaysPromoteToQueen,
    promotionSquare,
    setPromotionSquare,
    promotionStart,
    setPromotionStart,
    username,
    highlightColor,
    containsImage,
    highlighted,
    clearArrowsAndHighlights,
    castleViaRook,
    showHighlights,
    hidePieces,
    cancelPremove
}) {
    let [mouseIsOver, setMouseIsOver] = useState(false);

    let colorScheme = (name[0].charCodeAt(0) + parseInt(name[1])) % 2 === 1 ? 'light' : 'dark';

    let moves = game.moves;
    let movesIgnoringHandicap = game.movesIgnoringHandicap;

    let legal_premoves = game.legal_premoves?.[color];

    let lastMove = game.lastMove && (game.lastMove['start'] === name || game.lastMove['stop'] === name);
    
    let highlight = showHighlights && game?.highlights?.[highlightColor || color]?.includes(name);

    let promotionUiContents = null;
    let promotionUiContentsDict = null;

    if (promotionSquare) {
        if (promotionSquare[0] === name[0]) {
            if (promotionSquare[1] === '1') {
                promotionUiContentsDict = {
                    [promotionSquare]: { 'color': 'black', 'piece': 'queen' },
                    [`${promotionSquare[0]}2`]: { 'color': 'black', 'piece': 'knight' },
                    [`${promotionSquare[0]}3`]: { 'color': 'black', 'piece': 'rook' },
                    [`${promotionSquare[0]}4`]: { 'color': 'black', 'piece': 'bishop' },
                    [`${promotionSquare[0]}5`]: { 'piece': 'x' },
                }
            }
            else {
                promotionUiContentsDict = {
                    [promotionSquare]: { 'color': 'white', 'piece': 'queen' },
                    [`${promotionSquare[0]}7`]: { 'color': 'white', 'piece': 'knight' },
                    [`${promotionSquare[0]}6`]: { 'color': 'white', 'piece': 'rook' },
                    [`${promotionSquare[0]}5`]: { 'color': 'white', 'piece': 'bishop' },
                    [`${promotionSquare[0]}4`]: { 'piece': 'x' },
                }
            }
            promotionUiContents = promotionUiContentsDict?.[name];
        }
    }

    function legalMove(start, stop) {
        return moves && moves[start] && moves[start].filter((x) => x['stop'] === stop)[0];
    }

    function wouldBeLegalMoveExceptForHandicap(start, stop) {
        return movesIgnoringHandicap && movesIgnoringHandicap[start] && movesIgnoringHandicap[start].filter((x) => x['stop'] === stop)[0];
    }

    function legalPremove(start, stop) {
        return legal_premoves && legal_premoves[start] && legal_premoves[start].filter((x) => x['stop'] === stop)[0];
    }

    function submitMove(start, stop, promoteTo) {
        if (castleViaRook) {
            if (start == 'E1' && game.board[start].piece == 'king') {
                if (stop == 'H1') {
                    stop = 'G1';
                } if (stop == 'A1') {
                    stop = 'C1';
                }
            } else if (start == 'E8' && game.board[start].piece == 'king') {
                if (stop == 'H8') {
                    stop = 'G8';
                } if (stop == 'A8') {
                    stop = 'C8';
                }
            }
        }
        if (game.turn !== color) {
            if (start === stop) {
                cancelPremove();
            } else {
                if (!legalPremove(start, stop)) {
                    return;
                }
                let newGame = { ...game };
                if (newGame.board[start].piece === 'pawn' && (stop[1] === '1' || stop[1] === '8') && !alwaysPromoteToQueen && !promoteTo) {
                    setPromotionStart(start);
                    setPromotionSquare(stop);
                }
                else {
                    newGame.premoves[color] = { start, stop };
                    setGame(newGame);
                    fetchWrapper('/premove', { id: game.id, start, stop, color, promotion: promoteTo || 'queen', ignoreIfCheck: neverPremoveIntoCheck, username }, 'POST', port)
                        .then((response) => {
                            if (response.success) {
                                nullify(selectedPiece, setSelectedPiece);
                                setGame(response.game);
                                setPromotionStart(null);
                                setPromotionSquare(null);
                            }
                            else {
                                showError(response.error);
                            }
                        })
                    }
            }
        } else {
            if (!legalMove(start, stop)) {
                if (wouldBeLegalMoveExceptForHandicap(start, stop)) {
                    flashHandicap();
                }
                return;
            }
            let oldGame = { ...game };
            let newGame = { ...game };

            // make old board a copy so it doesn't update
            oldGame.board = { ...game.board };

            // en passant
            if (newGame.board[start].piece === 'pawn' && start[0] !== stop[0] && newGame.board[stop] === null) {
                newGame.board[stop[0] + start[1]] = null;
            }

            // promotion
            if (newGame.board[start].piece === 'pawn' && (stop[1] === '1' || stop[1] === '8')) {
                let move = moves?.[start]?.filter((x) => x['stop'] === stop)[0];
                const illegalPromotions = move?.['illegalPromotions'] || [];
                if (alwaysPromoteToQueen && !illegalPromotions.includes('queen')) {
                    newGame.board[stop] = { ...newGame.board[stop], color, piece: 'queen' };
                }
                else {
                    if (promoteTo && !illegalPromotions.includes(promoteTo)) {
                        newGame.board[stop] = { ...newGame.board[stop], color, piece: promoteTo };
                    } else {
                        if (promoteTo) {
                            showError('Illegal promotion');
                        }
                        setPromotionStart(start);
                        setPromotionSquare(stop);
                        return;
                    }
                }
            }

            else {
                newGame.board[stop] = newGame.board[start];
            }
            if (newGame.board[stop].piece === 'king' && start === 'E1') {
                if (stop === 'G1') {
                    newGame.board['F1'] = { piece: 'rook', color: 'white' };
                    newGame.board['H1'] = null;
                } else if (stop === 'C1') {
                    newGame.board['D1'] = { piece: 'rook', color: 'white' };
                    newGame.board['A1'] = null;
                }
            } else if (newGame.board[stop].piece === 'king' && start === 'E8') {
                if (stop === 'G8') {
                    newGame.board['F8'] = { piece: 'rook', color: 'black' };
                    newGame.board['H8'] = null;
                } else if (stop === 'C8') {
                    newGame.board['D8'] = { piece: 'rook', color: 'black' };
                    newGame.board['A8'] = null;
                }
            }
            newGame.board[start] = null;
            newGame.turn = newGame.turn === 'white' ? 'black' : 'white';
            newGame.lastMove = { start, stop };
            newGame.legal_premoves[color][stop] = makeLegalPremoves(stop, newGame.board[stop].piece, newGame.board[stop].color);
            newGame.temporary = true;
            const isCapture = moves?.[start]?.filter((x) => x['stop'] === name)[0]?.['capture'];
            const isCheck = moves?.[start]?.filter((x) => x['stop'] === name)[0]?.['inCheck'];
            const isChecking = moves?.[start]?.filter((x) => x['stop'] === name)[0]?.['checking'];
            playMoveSound(moveSound, captureSound, volume, isCapture);
            setGame(newGame);
            setPlayersInCheck({ ...playersInCheck, ...{ [color === 'white' ? 'black' : 'white']: isChecking }, ...{ [color]: isCheck } });

            if (promotionSquare) {
                setPromotionSquare(null);
                setPromotionStart(null);
            }
            fetchWrapper('/move', { id: game.id, start, stop, promotion: promoteTo, username, color }, 'POST', port)
                .then((response) => {
                    if (response.success) {
                        setGame(response.game);
                    } else {
                        setGame(oldGame);
                        showError(response.error);
                    }
                })
                    }
    }

    const handleMouseUp = (e) => {
        if (e.button === 2) {
            nullify(draggingPiece, setDraggingPiece);
            return
        }
        if (selectedPiece === name) {
            if (game?.premoves?.[color]) {
                cancelPremove();
            }
            nullify(selectedPiece, setSelectedPiece);
            nullify(draggingPiece, setDraggingPiece);
            return
        }
        if (draggingPiece) {
            if (draggingPiece === name) {
                nullify(draggingPiece, setDraggingPiece);
                setSelectedPiece(name);
            } else {
                submitMove(draggingPiece, name);
                nullify(draggingPiece, setDraggingPiece);
                nullify(selectedPiece, setSelectedPiece);
            }
        }
    }

    const onMouseEnter = () => {    
        setMouseIsOver(true);
    }

    const onMouseLeave = () => {
        setMouseIsOver(false);
    }

    const canActuallyDropFunc = (item) => {
        if (!item || !moves) {
            return false;
        }
        if (game.turn !== color) {
            return 'truthy value which is not true';
        }
        if (legalMove(item, name)) {
            return true;
        } return false;
    };

    const canActuallyDrop = canActuallyDropFunc(draggingPiece);

    let bgColors = {
        'red': { 'light': 'rgba(240, 140, 140, 1)', 'dark': 'rgba(210, 120, 120, 1)' },
        'green': { 'light': 'rgba(135, 152, 106, 255)', 'dark': 'rgba(106, 111, 66, 255)' },
        'darkGreen': { 'light': 'rgba(106, 111, 66, 255)', 'dark': 'rgba(78, 82, 44, 255)' },
        'blue': { 'light': 'rgba(0, 0, 255, 1)', 'dark': 'rgba(0, 0, 255, 1)' },
        'lastMove': { 'light': 'rgba(207, 209, 123, 255)', 'dark': 'rgba(172, 162, 73, 255)' },
        'purple': { 'light': 'rgba(130, 124, 134, 255)', 'dark': 'rgba(101, 83, 94, 255)' },
        'white': { 'light': 'rgba(255, 255, 255, 1)', 'dark': 'rgba(255, 255, 255, 1)' },
        'orange': { 'light': 'rgba(255, 165, 0, 1)', 'dark': 'rgba(255, 165, 0, 1)' },
        // 'yellow': {'light': 'rgba(255, 255, 0, 1)', 'dark': 'rgba(255, 255, 0, 1)'},
    }

    function x(color) {
        if (!color) return {
            outline: '2px solid black',
        }

        return {
            backgroundColor: bgColors[color][colorScheme],
            // outline: '2px solid black',
        }
    }

    let movingPiece = draggingPiece || selectedPiece;
    let premove = game.premoves && game.premoves[color];

    let isPremove = premove && [premove['start'], premove['stop']].includes(name);

    const legalMoveOutput = legalMove(movingPiece, name);

    let canMove = canActuallyDrop || !!(!draggingPiece && legalMoveOutput && !game.result);

    let isKingEnPassantCapture = canMove && legalMoveOutput && legalMoveOutput.kingEnPassantCapture;

    let isCheck = canMove && moves?.[movingPiece]?.filter((x) => x['stop'] === name)[0]?.['inCheck'];

    let highlightMove = canMove && moves?.[movingPiece]?.filter((x) => x['stop'] === name)[0]?.['highlight'];

    let premovingPiece = draggingPiece || selectedPiece;

    let canPremove = !!(legalPremove(premovingPiece, name) && !game.result) && game.turn !== color;

    let style = promotionUiContents ? { cursor: 'pointer' } : canActuallyDrop !== false ? { cursor: 'grabbing' } : {};
    style = lastMove && !(canMove === true || canPremove === true) && !hidePieces ? { ...style, ...x('lastMove') } : style;
    style = draggingPiece === name ? { ...style, ...x('green') } : style;
    style = !draggingPiece && selectedPiece === name ? { ...style, ...x('green') } : style;
    // style = canMove === true ? { ...style, ...x('blue') } : style;
    // style = canPremove === true ? { ...style, ...x('blue') } : style;
    // style = isCheck === true ? { ...style, ...x('red') } : style;
    style = highlight ? { ...style, ...x('red') } : style;
    style = isPremove ? { ...style, ...x('purple') } : style;
    style = promotionUiContents ? { ...style, ...x('white') } : style;
    style = mouseIsOver && canActuallyDrop === true ? { ...style, outline: '2px solid red', zIndex: 1001 } : style;
    style = { ...style, width: dimensions, height: dimensions };

    const darkRed = colorScheme === 'dark' ? '#AA0000' : '#CC0000';
    const canMoveColor = (game.turn !== color) ? bgColors['purple'][colorScheme] : isCheck === true ? darkRed : highlightMove === true ? bgColors['orange'][colorScheme] : bgColors['darkGreen'][colorScheme];

    const isInCheck = (playersInCheck['white'] && contents?.piece === 'king' && contents?.color === 'white') || (playersInCheck['black'] && contents?.piece === 'king' && contents?.color === 'black');

    const shouldHidePiece = hidePieces && contents?.color !== color && !isInCheck;

    function onClick(e) {
        if (e.button === 2) {
            nullify(draggingPiece, setDraggingPiece);
            cancelPremove();
            return
        }
        if (!game.current) {
            return;
        }
        if (promotionUiContents) {
            if (promotionUiContents.piece === 'x') {
                setPromotionSquare(null);
                setPromotionStart(null);
                return;
            }
            submitMove(promotionStart, promotionSquare, promotionUiContents.piece);
            return;
        }
        if (premove) {
            cancelPremove();
            if (contents && contents.color === color) {
                setSelectedPiece(name);
            }
            return
        }
        if (canActuallyDrop === false && !game.result) {
            if (selectedPiece && selectedPiece === name) {
                submitMove(selectedPiece, name);
                nullify(selectedPiece, setSelectedPiece);
            }
            else if (selectedPiece) {
                submitMove(selectedPiece, name);
                setSelectedPiece(contents && contents.color === color && game.turn === color ? name : null);
            }
            else if (contents && contents.color === color) {
                setSelectedPiece(name);
            }
        }
    }

    const draggable = !game.result && game.current && (contents?.color === color) && (canActuallyDrop === false) && !((selectedPiece && selectedPiece != name) && game.turn !== color);

    return (
        <div
            draggable={false}
            className={`square ${colorScheme} ${display} triangle-corners`}
            style={style}
            onMouseUp={handleMouseUp}
            onMouseDown={onClick}
            onMouseEnter={onMouseEnter}
            onMouseLeave={onMouseLeave}
            onMouseMove={() => setMouseIsOver(true)}
        >
            {/* <div className="square-name">{name}</div> */}
            <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
            }}>
                <div
                    cx="0"
                    cy="0"
                    r="0.01"
                    fill="none"
                    stroke="black"
                    strokeWidth="0.2"
                    ref={squareRef}
                    style={{ visibility: 'hidden' }}
                />
            </div>
            {highlighted && (
                <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    width: '100%',
                    height: '100%',
                    transform: 'translate(-50%, -50%)',
                }}>
                    <svg width="125%" height="125%">
                        <circle cx="40%" cy="40%" r="38%" fill="none" stroke="rgba(0, 128, 0, 0.7)" strokeWidth="5%" />
                    </svg>
                </div>
            )}
            {promotionUiContents && <ChessPiece
                contents={promotionUiContents}
                dimensions={dimensions}
                location={name}
                draggable={false}
                setDraggingPiece={setDraggingPiece}
                isInCheck={false}
            />}
            {!promotionUiContents && contents && !shouldHidePiece && !isKingEnPassantCapture && <ChessPiece
                contents={contents}
                dimensions={dimensions}
                location={name}
                draggable={draggable}
                draggingPiece={draggingPiece}
                setDraggingPiece={setDraggingPiece}
                isInCheck={isInCheck}
                clearArrowsAndHighlights={clearArrowsAndHighlights}
                cancelPremove={cancelPremove}
            />}
            {(canMove === true || canPremove === true) && !contents && !isKingEnPassantCapture && <div style={{
                position: 'absolute',
                width: '35%',
                height: '35%',
                borderRadius: '50%',
                backgroundColor: canMoveColor,
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)'
            }} />}
            {isKingEnPassantCapture && <ChessPiece
                contents={{piece: 'king', color: color === 'white' ? 'black' : 'white'}}
                dimensions={dimensions}
                location={name}
                draggable={false}
                setDraggingPiece={setDraggingPiece}
                isInCheck={true}
                opacity={0.25}
            />}
            {!promotionUiContents && !contents && !canMove && !canPremove && containsImage && <div style={{ width: dimensions, height: dimensions }}>
                <img
                    src={`${process.env.PUBLIC_URL}/assets/${containsImage}.png`}
                    alt={containsImage}
                    style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        width: '100%',
                        height: '100%',
                    }} />
            </div>
            }
            {display.includes('rank') && <div className="square-rank">{name[1]}</div>}
            {display.includes('file') && <div className="square-file">{name[0]}</div>}
            {(((canMove === true || canPremove === true) && contents) || isKingEnPassantCapture) &&
                <>
                    {/* <div className="triangle-top-left"></div> */}
                    <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: 0,
                        height: 0,
                        borderBottom: `${triangleDimensions} solid transparent`,
                        borderRight: `${triangleDimensions} solid transparent`,
                        borderTop: `${triangleDimensions} solid ${canMoveColor}`,
                        borderLeft: `${triangleDimensions} solid ${canMoveColor}`,
                    }}></div>
                    <div style={{
                        position: 'absolute',
                        top: 0,
                        right: 0,
                        width: 0,
                        height: 0,
                        borderBottom: `${triangleDimensions} solid transparent`,
                        borderLeft: `${triangleDimensions} solid transparent`,
                        borderTop: `${triangleDimensions} solid ${canMoveColor}`,
                        borderRight: `${triangleDimensions} solid ${canMoveColor}`,
                    }}></div>
                    <div style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        width: 0,
                        height: 0,
                        borderTop: `${triangleDimensions} solid transparent`,
                        borderRight: `${triangleDimensions} solid transparent`,
                        borderBottom: `${triangleDimensions} solid ${canMoveColor}`,
                        borderLeft: `${triangleDimensions} solid ${canMoveColor}`,
                    }}></div>
                    <div style={{
                        position: 'absolute',
                        bottom: 0,
                        right: 0,
                        width: 0,
                        height: 0,
                        borderTop: `${triangleDimensions} solid transparent`,
                        borderLeft: `${triangleDimensions} solid transparent`,
                        borderBottom: `${triangleDimensions} solid ${canMoveColor}`,
                        borderRight: `${triangleDimensions} solid ${canMoveColor}`,
                    }}></div>

                    {/* <div className="triangle-top-right"></div>
                    <div className="triangle-bottom-left"></div>
                    <div className="triangle-bottom-right"></div> */}
                </>
            }
        </div>
    );
}
