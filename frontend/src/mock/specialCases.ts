import * as data from './mockData';

export const specialCases: Record<string, Record<string, any>> = {
    'ERROR_500': {
        status: 500,
        data: { success: false, message: 'Internal Server Error (Mocked)' }
    },
    'ERROR_403': {
        status: 403,
        data: { success: false, message: 'Forbidden: Access Denied' }
    },
    'AUTH_401': {
        status: 401,
        data: { success: false, message: 'Unauthorized: Session Expired' }
    },
    'EMPTY_STATE': {
        status: 200,
        data: { success: true, data: [], message: 'No records found' }
    },
    'LONG_LATENCY': {
        status: 200,
        delay: 5000,
        data: { success: true, data: data.mockKBs.slice(0, 3), message: 'Success after 5s' }
    },
    'MALFORMED_DATA': {
        status: 200,
        data: { unexpected_field: 'This is not the standard ApiResponse format' }
    },
    'MAX_CONTENT': {
        status: 200,
        data: {
            success: true,
            data: Array.from({ length: 100 }).map((_, i) => ({
                ...data.mockKBs[0],
                id: `kb-max-${i}`,
                name: `极长标题测试 - ${'很长'.repeat(20)} - ${i}`,
                description: '重复描述'.repeat(50)
            }))
        }
    }
};
