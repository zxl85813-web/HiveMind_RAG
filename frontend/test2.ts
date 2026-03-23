import { MultiTrackParser } from './src/core/stream/MultiTrackParser';

const parser = new MultiTrackParser();
parser.on('content', (data) => console.log('CONTENT:', data));

parser.parse('{"track": "content", "type": "content", "delta": "I survived the rate limit storm!"}');
parser.parse('{"track": "content", "type": "content", "content": "I survived the rate limit storm!"}');
parser.parse('{"track": "done", "type": "done"}');
