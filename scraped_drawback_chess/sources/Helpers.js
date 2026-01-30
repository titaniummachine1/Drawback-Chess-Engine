import { baseURL } from './Settings';

let userHasInteracted = false;

function log(str) {
    if (localStorage.getItem('log')) {
        console.log(str);
    }
}

window.addEventListener('mousedown', () => {
    userHasInteracted = true;
});

window.addEventListener('keydown', () => {
    userHasInteracted = true;
});

export function makeRequestOptions(body, method = 'POST') {
    if (method === 'GET') {
        return {
            method,
            mode: 'cors',
            headers: { 'Content-Type': 'application/json' },
        };
    }
    return {
        method,
        mode: 'cors',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    };
}

function randomPort() {
    return localStorage.getItem('dc-port') || Math.floor(Math.random() * 16) + 5001;
}

function playWithCatch(audio) {
    try {
        const playPromise = audio.play();

        if (playPromise !== undefined) {
            playPromise.then(_ => {
                // Audio playback started successfully
            }).catch(error => {
                console.error('Error playing sound:', error);
            });
        }
    } catch (error) {
        console.error('Error playing sound:', error);
    }
}
export function fetchWrapper(url, body, method = 'POST', port = null) {
    port = process.env.REACT_APP_LOCAL ? 5001 : (port || randomPort());
    
    // let fullUrl = `${baseURL}:${port}${url}`;
    let fullUrl = `${baseURL}/app${port - 5000}${url}`
    if (process.env.REACT_APP_LOCAL) {
        port = '5050';
        fullUrl = `${baseURL}:${port}${url}`;
    } 

    if (method === 'GET') {
        if (body) {
            const queryParams = new URLSearchParams(body).toString();
            fullUrl = `${fullUrl}?${queryParams}`;
        }
    }
    return fetch(fullUrl, makeRequestOptions(body, method))
        .then(response => {
            if (!response.ok) {
                // Always print this
                console.log(response.json());
                return {
                    'success': false,
                    'error': `Unexpected error on ${url}`,
                }
            }
            return response.json();
        })
        .catch((error) => {
            return {
                'success': false,
                'error': error.message,
            }
        });
}

export function playWrongSound(wrongSound, volume) {
    if (!userHasInteracted && process.env.REACT_APP_LOCAL) return;
    if (!volume) return;

    try {
        let audio = new Audio(wrongSound);
        audio.volume = 0.35 * volume / 100;
        playWithCatch(audio);
    } catch (error) {
        console.error('Error playing sound:', error);
    }
}

export function playMoveSound(moveSound, captureSound, volume, isCapture) {
    log('userHasInteracted', userHasInteracted);
    
    if (!userHasInteracted && process.env.REACT_APP_LOCAL) return;
    if (!volume) return;

    try {
        if (isCapture) {
            let audio = new Audio(captureSound);
            audio.volume = 0.7 * volume / 100;
            playWithCatch(audio);
        } else {
            let audio = new Audio(moveSound);
            audio.volume = 0.7 * volume / 100;
            playWithCatch(audio);
        }
    } catch (error) {
        console.error('Error playing sound:', error);
    }
}

export function playNotifySound(notifySound, volume) {
    if (!userHasInteracted && process.env.REACT_APP_LOCAL) return;
    if (!volume) return;

    try {
        let audio = new Audio(notifySound);
        audio.volume = 0.6 * volume / 100;
        playWithCatch(audio);
    } catch (error) {
        console.error('Error playing sound:', error);
    }    
}

export function playLowTimeSound(lowTimeSound, volume) {
    if (!userHasInteracted && process.env.REACT_APP_LOCAL) return;
    if (!volume) return;

    try {
        let audio = new Audio(lowTimeSound);
        audio.volume = 0.5 * volume / 100;
        playWithCatch(audio);
    } catch (error) {
        console.error('Error playing sound:', error);
    }
}

export function getUsername(length, openDialog) {
    if (localStorage.getItem('dc-username')) {
        return localStorage.getItem('dc-username');
    }
    let result = '';
    let characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let charactersLength = characters.length;
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    localStorage.setItem('dc-username', result);
    openDialog && openDialog();
    return result;
}
