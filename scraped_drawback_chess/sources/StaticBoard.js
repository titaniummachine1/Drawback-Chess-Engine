import React, { useMemo } from 'react';
import ChessPiece from './ChessPiece';
import { boardOrder } from './GamePage';
import './Styles.css';
import { imageUrl } from './ChessPiece';

export default function StaticBoard({
    board,
    squareWidth,
    display,
    orientation, 
}) {
    if (!board) {
        return null;
    }

    return (
        <div className="board" style={{width: `${8*squareWidth}px`}}>
            {boardOrder(orientation).map((key) => (
                <StaticSquare
                    key={key}
                    contents={board[key]}
                    dimensions={`${squareWidth}px`}
                    display={display}
                    name={key}
                />
            ))}
        </div>
    )
}

function StaticSquare({
    contents,
    dimensions,
    display,
    name,
}) {
    let colorScheme = (name[0].charCodeAt(0) + parseInt(name[1])) % 2 === 1 ? 'light' : 'dark';
    const style = {width: dimensions, height: dimensions};

    return (
        <div
            className={`square ${colorScheme} ${display} triangle-corners`}
            style={style}
        >
            {display.includes('rank') && <div className="square-rank">{name[1]}</div>}
            {display.includes('file') && <div className="square-file">{name[0]}</div>}
            {contents && <StaticChessPiece
                contents={contents} 
                dimensions={dimensions} 
            />}
        </div>
    )
}

const StaticChessPiece = ({ contents, dimensions }) => {
    const style = {
        width: dimensions,
        height: dimensions,
    }


    return (
        <div
            className="chess-piece"
            style={style}
        >
            <img
                src={imageUrl(contents, false)} 
                alt={contents?.piece} 
                style={{ 
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',                    
                    width: '100%', 
                    height: '100%', 
                }} />
        </div >
    );
}
