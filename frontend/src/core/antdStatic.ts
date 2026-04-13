import type { MessageInstance } from 'antd/es/message/interface';
import type { ModalStaticFunctions } from 'antd/es/modal/confirm';
import type { NotificationInstance } from 'antd/es/notification/interface';

let message: MessageInstance;
let notification: NotificationInstance;
let modal: ModalStaticFunctions;

export default {
    get message() {
        return message;
    },
    get notification() {
        return notification;
    },
    get modal() {
        return modal;
    },
};

export const setStaticHelpers = (
    _message: MessageInstance,
    _notification: NotificationInstance,
    _modal: ModalStaticFunctions
) => {
    message = _message;
    notification = _notification;
    modal = _modal;
};
