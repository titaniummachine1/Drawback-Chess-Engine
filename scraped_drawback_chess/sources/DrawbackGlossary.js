import React, { useEffect, useState } from 'react';
import { Grid, Card, CardContent, Typography, Button, Select, MenuItem, TextField } from '@mui/material';
import { fetchWrapper, getUsername } from './Helpers';
import { useNavigate } from 'react-router-dom';

import { playNotifySound } from './Helpers';
import notifySound from './assets/notify.mp3';

import AcceptChallengeDialog from './AcceptChallengeDialog';
import Toast from './Toast';

import io from 'socket.io-client';

import { baseURL } from './Settings';

function log(str) {
  if (localStorage.getItem('log')) {
    console.log(str);
  }
}

function pos(elo) {
  let values = [
    [-5000, 100],
    [-400, 95],
    [0, 90],
    [400, 85],
    [800, 70],
    [1200, 50],
    [1600, 30],
    [2000, 15],
    [2400, 5],
    [5000, 0],
  ]

  for (let i = 0; i < values.length - 1; i++) {
    if (elo === values[i][0]) {
      return values[i][1];
    }
    if (elo > values[i][0] && elo < values[i + 1][0]) {
      let y1 = values[i][1];
      let y2 = values[i + 1][1];
      let x1 = values[i][0];
      let x2 = values[i + 1][0];
      let y = y1 + (y2 - y1) * ((elo - x1) / (x2 - x1));
      return y;
    }
  }

}

export const DrawbackDifficultyScale = ({ elo, infrequentNotches }) => {
  const position = pos(elo);

  const interval = infrequentNotches ? 400 : 200; // Define the interval for notches

  return (
    <div style={{
      // width: '100%', 
      height: '70px',
      border: '2px solid #fff',
      background: 'linear-gradient(to right, green, red)',
      borderRadius: '40px',
      overflow: 'hidden',
      position: 'relative',
      boxShadow: '8px 8px 20px rgba(0, 0, 0, 0.5)' // Adding shadow
    }}>
      <div style={{ position: 'absolute', left: '0', top: '50%', transform: 'translateY(-50%)', paddingLeft: '20px', color: '#fff', fontSize: '22px' }}>Easy</div>
      <div style={{ position: 'absolute', right: '0', top: '50%', transform: 'translateY(-50%)', paddingRight: '20px', color: '#fff', fontSize: '22px' }}>Hard</div>
      {/* <div style={{ position: 'absolute', left: `${position}%`, top: '50%', transform: 'translate(-50%, -50%)', width: 0, height: '100%', borderLeft: '2px solid white' }}></div>             */}
      <div style={{ position: 'absolute', left: `${position}%`, bottom: 0, transform: 'translateX(-50%)', width: 0, height: 0, borderLeft: '10px solid transparent', borderRight: '10px solid transparent', borderBottom: '16px solid white' }}></div>
      <div style={{ position: 'absolute', left: `${position}%`, top: 0, transform: 'translateX(-50%)', width: 0, height: 0, borderLeft: '10px solid transparent', borderRight: '10px solid transparent', borderTop: '16px solid white' }}></div>
      {[...Array(2800 / interval)].map((_, index) => (
        <div key={index} style={{ position: 'absolute', left: `${(index + 1) * interval / 12}%`, top: 0, width: 0, height: '100%', borderLeft: '2px dashed white' }}></div>
      ))}
    </div>
  );
};

export const DrawbackDifficultyScaleForTwoPlayers = ({ yourElo, yourColor, opponentElo, opponentColor, infrequentNotches }) => {
  const yourPosition = pos(yourElo);
  const opponentPosition = pos(opponentElo);

  const interval = infrequentNotches ? 400 : 200; // Define the interval for notches

  return (
    <div style={{ overflow: 'hidden' }}>
      <Typography style={{ fontSize: 15, position: 'relative', left: `${Math.max(10, Math.min(opponentPosition, 90))}%`, transform: 'translateX(-50%)', textAlign: 'center', color: 'white', marginBottom: '5px' }}>
        Opponent
      </Typography>
      <div style={{
        height: '70px',
        background: 'linear-gradient(to right, green, red)',
        borderRadius: '40px',
        position: 'relative',
        boxShadow: '8px 8px 20px rgba(0, 0, 0, 0.5)' // Adding shadow
      }}>
        <div style={{ position: 'absolute', left: '0', top: '50%', transform: 'translateY(-50%)', paddingLeft: '20px', color: '#fff', fontSize: '22px' }}>Easy</div>
        <div style={{ position: 'absolute', right: '0', top: '50%', transform: 'translateY(-50%)', paddingRight: '20px', color: '#fff', fontSize: '22px' }}>Hard</div>
        {[...Array(2800 / interval)].map((_, index) => (
          <div key={index} style={{ position: 'absolute', left: `${(index + 1) * interval / 12}%`, top: 0, width: 0, height: '100%', borderLeft: '2px dashed #888' }}></div>
        ))}
        <div style={{ position: 'absolute', left: `${yourPosition}%`, bottom: 0, transform: 'translateX(-50%)', width: 0, height: 0, borderLeft: '10px solid transparent', borderRight: '10px solid transparent', borderBottom: `16px solid ${yourColor}` }}></div>
        <div style={{ position: 'absolute', left: `${opponentPosition}%`, top: 0, transform: 'translateX(-50%)', width: 0, height: 0, borderLeft: '10px solid transparent', borderRight: '10px solid transparent', borderTop: `16px solid ${opponentColor}` }}></div>
      </div>
      <Typography style={{ fontSize: 15, position: 'relative', left: `${yourPosition}%`, transform: 'translateX(-50%)', textAlign: 'center', color: 'white', marginTop: '5px' }}>
        You
      </Typography>
    </div>
  );
}

export function DrawbackDisplay({ handicap, handicaps, setHandicaps, small, showMessage }) {
  const setOpinion = (handicap, opinion) => {
    log('Setting opinion: ', handicap.name, opinion)

    const newHandicaps = handicaps.map(h => {
      if (h.name === handicap.name) {
        return {
          ...h,
          opinion: opinion
        };
      } else {
        return h;
      }
    });

    setHandicaps(newHandicaps);

    fetchWrapper('/set_opinion', {
      username: getUsername(20),
      handicap: handicap.name,
      opinion: opinion
    }, 'POST')
      .then(response => {
        if (!response.success) {
          console.error('Error setting opinion: ', response.error);
        } else if (showMessage && response.message) {
          showMessage(response.message);
        }
      });
  };

  const buttonStyle = (opinion, on) => ({
    width: small ? '80px' : '100px',
    height: small ? '80px' : '100px',
    backgroundColor: on ? (opinion === 1 ? 'lightgreen' : opinion === 0 ? '#888888' : opinion === -1 ? '#FF8888' : 'lightgray') : 'lightgray'
  });

  const imageStyle = {
    maxWidth: '100%',
    maxHeight: '100%'
  };

  return (
    <Grid container style={{ alignItems: 'center', justifyContent: 'center' }} direction="row" item xs={12} spacing={small ? 2 : 3}>
      <Grid item>
        <Button variant="contained" style={buttonStyle(handicap.opinion, handicap.opinion === 1)} onClick={() => setOpinion(handicap, 1)}>
          <img style={imageStyle} src={`${process.env.PUBLIC_URL}/assets/green-thumbs-up.png`} alt="Like" />
        </Button>
      </Grid>
      <Grid item>
        <Button variant="contained" style={buttonStyle(handicap.opinion, handicap.opinion === 0)} onClick={() => setOpinion(handicap, 0)}>
          {/* Empty Button */}
        </Button>
      </Grid>
      <Grid item>
        <Button variant="contained" style={buttonStyle(handicap.opinion, handicap.opinion === -1)} onClick={() => setOpinion(handicap, -1)}>
          <img style={imageStyle} src={`${process.env.PUBLIC_URL}/assets/red-thumbs-down.png`} alt="Dislike" />
        </Button>
      </Grid>
    </Grid>
  );
}

const DrawbackGlossary = ({ showAll }) => {
  const [drawbackError, setDrawbackError] = useState(null);
  const [handicaps, setHandicaps] = useState([]);
  const [preference, setPreference] = useState(null);
  const [sortBy, setSortBy] = useState('Name');
  const [nameFilter, setNameFilter] = useState('');
  const [availabilityFilter, setAvailabilityFilter] = useState('All');
  const [order, setOrder] = useState('Ascending');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const username = getUsername(20);

  let [socket, setSocket] = useState(null);

  let [acceptChallengeDialogOpen, setAcceptChallengeDialogOpen] = useState(false);
  let [challengerDisplayName, setChallengerDisplayName] = useState('');
  let [challengeGameId, setChallengeGameId] = useState(null);
  let [challengeFriendshipId, setChallengeFriendshipId] = useState(null);
  let port = 5050;

  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

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
    let password = localStorage.getItem('glossary-password');
    if (showAll && !password) {
      password = prompt('Enter password');
    }
    fetchWrapper('/handicap_glossary', { username: getUsername(20), showAll: showAll || '', password }, 'GET')
      .then(response => {
        if (response.success) {
          setHandicaps(response.handicaps);
          setPreference(response.preference);
          setLoading(false);
        } else {
          setDrawbackError(response.error);
          showError(response.error);
          setLoading(false);
        }
      });
  }, []);

  const setHandicapPreference = (preference) => {
    let oldPreference = preference;
    setPreference(preference);

    fetchWrapper('/set_handicap_preference', {
      username: getUsername(20),
      preference: preference
    }, 'POST')
      .then(response => {
        if (!response.success) {
          setPreference(oldPreference);
          showError(response.error);
        }
      });
  }

  if (loading) {
    return <h1>Loading...</h1>;
  }

  if (drawbackError) {
    return <h1>{drawbackError}</h1>;
  }

  const cardStyle = {
    backgroundColor: '#444488',
    color: 'white',
    minHeight: '100px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    width: '400px',
    textAlign: 'center'
  };

  let sortedHandicaps = [...handicaps].sort((a, b) => {
    if (sortBy === 'Name') {
      return a.name.localeCompare(b.name);
    } else if (sortBy === 'Difficulty') {
      return b.elo - a.elo;
    } else if (sortBy === 'Opinion') {
      return a.opinion - b.opinion;
    } else if (sortBy === 'My Performance') {
      let aRate = (a.wins + 1 + a.draws / 2) / (a.wins + a.draws + a.losses + 2);
      if (a.wins + a.draws + a.losses == 0) {
        aRate = -1;
      }
      let bRate = (b.wins + 1 + b.draws / 2) / (b.wins + b.draws + b.losses + 2);
      if (b.wins + b.draws + b.losses == 0) {
        bRate = -1;
      }
      return aRate - bRate;
    }
    else {
      return 0;
    }
  });

  if (order === 'Descending') {
    sortedHandicaps = sortedHandicaps.reverse();
  }

  let allAvaibilities = sortedHandicaps.map(h => h.availability).filter((value, index, self) => self.indexOf(value) === index);

  if (sortBy == 'My Performance') {
    sortedHandicaps = sortedHandicaps.filter(h => h.wins + h.draws + h.losses > 0);
  }

  if (nameFilter) {
    sortedHandicaps = sortedHandicaps.filter(h => h.name.toLowerCase().includes(nameFilter.toLowerCase()));
  }

  if (availabilityFilter !== 'All') {
    sortedHandicaps = sortedHandicaps.filter(h => h.availability.toLowerCase() == availabilityFilter.toLowerCase());
  }

  return (
    <>
      <div style={{ width: '100%', display: 'flex', justifyContent: 'center', position: 'fixed', left: 0, top: 10, zIndex: 9999 }}>
        {error && <Toast message={error} onClose={() => setError(null)} />}
        {message && <Toast message={message} onClose={() => setMessage(null)} isError={false} />}
      </div>
      <Grid container direction="column" spacing={3}>
        <Grid item>
          <Typography style={{ fontSize: 36 }}>
            Drawback glossary
          </Typography>
          <br />
          <Grid item>
            <Button variant="contained" style={{ marginBottom: 20 }} onClick={() => navigate('/')}>
              Back to home
            </Button>
          </Grid>
          Drawback difficulty ratings are calculated adaptively using an elo system. Your games help us determine how difficult each drawback is! If you are a higher rated player than your opponent, you will generally get a harder drawback.
          <br />
          <br />
          You can request generally harder or easier drawbacks. There's no guarantees, since we'll still try to have a somewhat balanced game, but we'll try to err on the side of your preference. The colored-in button represents your current choice.
          <br />
          <br />
          <Grid container direction="row" spacing={3}>
            <Grid item>
              <Button variant={preference == 1 ? "contained" : "outlined"} style={{ marginBottom: 20 }} onClick={() => setHandicapPreference(1)}>
                I prefer hard drawbacks!
              </Button>
            </Grid>
            <Grid item>
              <Button variant={preference == 0 ? "contained" : "outlined"} style={{ marginBottom: 20 }} onClick={() => setHandicapPreference(0)}>
                Give me whatever!
              </Button>
            </Grid>
            <Grid item>
              <Button variant={preference == -1 ? "contained" : "outlined"} style={{ marginBottom: 20 }} onClick={() => setHandicapPreference(-1)}>
                I prefer easy drawbacks!
              </Button>
            </Grid>
          </Grid>
          <Grid item>
            Sort by:
            <Select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ marginLeft: '10px' }}>
              <MenuItem default value="Name">Name</MenuItem>
              <MenuItem value="Difficulty">Difficulty</MenuItem>
              <MenuItem value="My Performance">My Performance</MenuItem>
              <MenuItem value="Opinion">Opinion</MenuItem>
            </Select>
            <Select value={order} onChange={e => setOrder(e.target.value)} style={{ marginLeft: '10px' }}>
              <MenuItem value="Ascending">Ascending</MenuItem>
              <MenuItem value="Descending">Descending</MenuItem>
            </Select>
          </Grid>
          <Grid item style={{ marginTop: '10px' }}>
            <TextField label="Filter by name" value={nameFilter} onChange={e => setNameFilter(e.target.value)} />
            <Select value={availabilityFilter} onChange={e => setAvailabilityFilter(e.target.value)} style={{ marginLeft: '10px' }}>
              <MenuItem value="All">All</MenuItem>
              {allAvaibilities.map((availability, index) => (
                <MenuItem value={availability} key={index}>{availability}</MenuItem>
              ))}
            </Select>
          </Grid>
        </Grid>
        {sortedHandicaps.map((handicap, index) => (
          <Grid container style={{ alignItems: 'center' }} item xs={12} spacing={3} key={index} direction="row">
            <Grid item>
              <Card style={cardStyle}>
                <CardContent>
                  <Typography variant="h6" component="h2" style={{ fontWeight: 'bold' }}>
                    {handicap.name}
                  </Typography>
                  <Typography variant="body2" component="p">
                    {handicap.description}
                  </Typography>
                  {showAll && <Typography variant="body2" component="p">
                    Elo: {handicap.elo}
                  </Typography>}
                  {handicap.wins + handicap.draws + handicap.losses ?
                    <Typography variant="body2" component="p">
                      Record as: {handicap.wins}W {handicap.draws}D {handicap.losses}L
                      ({((handicap.wins + handicap.draws * .5) / (handicap.wins + handicap.draws + handicap.losses)).toFixed(2)})
                    </Typography>
                    : null}
                  {handicap.winsAgainst + handicap.drawsAgainst + handicap.lossesAgainst ?
                    <Typography variant="body2" component="p">
                      Record against: {handicap.winsAgainst}W {handicap.drawsAgainst}D {handicap.lossesAgainst}L
                      ({((handicap.winsAgainst + handicap.drawsAgainst * .5) / (handicap.winsAgainst + handicap.drawsAgainst + handicap.lossesAgainst)).toFixed(2)})
                    </Typography>
                    : null}
                </CardContent>
                <div style={{ "width": '90%', "marginBottom": '20px' }}>
                  <DrawbackDifficultyScale elo={handicap.elo} infrequentNotches />
                </div>
              </Card>
            </Grid>
            {!showAll && <Grid item>
              <DrawbackDisplay handicap={handicap} key={index} handicaps={handicaps} setHandicaps={setHandicaps} />
            </Grid>}
          </Grid>
        ))}
        <Grid item>
          <Typography style={{ fontSize: 20 }}>
            Play more games to discover more drawbacks!
          </Typography>
        </Grid>
        <Grid item>
          <Button variant="contained" style={{ marginBottom: 20 }} onClick={() => navigate('/')}>
            Back to home
          </Button>
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
};

export default DrawbackGlossary;