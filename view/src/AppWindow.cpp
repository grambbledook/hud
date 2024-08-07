#include <QPainter>
#include "AppWindow.h"

#include <iostream>

#include "Constants.h"

AppWindow::AppWindow(const std::shared_ptr<ControllerHandler> &handler, QWidget *parent) : QMainWindow(parent),
                                                                                           m_drag(false), m_DragPosition(QPoint(0, 0)), controllerHandler(handler) {

    setWindowFlags(Qt::WindowType::WindowStaysOnTopHint | Qt::WindowType::FramelessWindowHint);
    setAttribute(Qt::WidgetAttribute::WA_TranslucentBackground, true);
    setObjectName(Constants::Classes::APP_WINDOW);
}

AppWindow::~AppWindow() = default;

// void AppWindow::paintEvent(QPaintEvent *event) {
    // const auto painter = std::make_unique<QPainter>(this);

    // painter->setOpacity(0.25);
    // painter->setBrush(QBrush(QColor(200, 200, 200, 128)));
    // painter->drawRect(this->rect());
// }


void AppWindow::mousePressEvent(QMouseEvent *event) {
    if (event->button() == Qt::MouseButton::LeftButton) {
        m_drag = true;
        m_DragPosition = event->globalPosition() - this->pos();

        event->accept();
    }
}

void AppWindow::mouseMoveEvent(QMouseEvent *event) {
    if (event->buttons() == Qt::MouseButton::LeftButton && m_drag) {
        const auto newPosition = event->globalPosition() - m_DragPosition;
        this->move(newPosition.toPoint());

        event->accept();
    }
}

void AppWindow::mouseReleaseEvent(QMouseEvent *event) {
    m_drag = false;

    update();
}

void AppWindow::back() {
    std::cout << "AppWindow::back" << std::endl;
}

void AppWindow::next() {
    std::cout << "AppWindow::next" << std::endl;
}

bool AppWindow::event(QEvent *event) {
    if (event->type() <= QEvent::MaxUser and event->type() >= QEvent::User) {
        std::cout << "AppWindow::event: " << event->type() << " | " << typeid(event).name() << std::endl;
        const int device_selected_type = getDeviceSelectedType();
        std::cout << "  DeviceSelectedType id:" << device_selected_type << std::endl;

        const int device_discovered_type = getDeviceDiscoveredType();
        std::cout << "  DeviceDiscoveredType id:" << device_discovered_type << std::endl;

        if (eventHandlers.contains(event->type())) {
            eventHandlers[event->type()](event);
            return true;
        }

        std::cout << "  Handler not found!" << std::endl;
        std::cout << "  Handlers:" << std::endl;
        for (const auto &[key, _] : eventHandlers) {
            std::cout << "    " << key << std::endl;
        }
    }

    if (eventHandlers.contains(event->type())) {
        eventHandlers[event->type()](event);
        return true;
    }

    return QMainWindow::event(event);
}
