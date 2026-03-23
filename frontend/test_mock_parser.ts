import { MultiTrackParser } from './src/core/stream/MultiTrackParser';

const parser = new MultiTrackParser();
parser.on('content', (data) => console.log('CONTENT:', data));

parser.parse('{"track": "content", "type": "con');
