#!/usr/bin/env python


import math

from PyQt5.QtCore import (qAbs, QLineF, QPointF, QRectF, qrand, qsrand, Qt,
        QTime, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter, QPainterPath, QPixmap,
        QPolygonF)
from PyQt5.QtWidgets import (QApplication, QGraphicsItem, QGraphicsEllipseItem, QGraphicsScene,
        QGraphicsView, QGraphicsWidget, QPushButton, QWidget, QGridLayout)

import sys


class Mouse(QGraphicsItem):
    Pi = math.pi
    TwoPi = 2.0 * Pi

    # Create the bounding rectangle once.
    adjust = 0.5
    BoundingRect = QRectF(-20 - adjust, -22 - adjust, 40 + adjust, 40 + adjust)

    def __init__(self, driver):
        super(Mouse, self).__init__()

        self.driver = driver
        self.angle = 0.0
        self.speed = 0.0
        self.mouseEyeDirection = 0.0
        self.color = QColor(qrand() % 256, qrand() % 256, qrand() % 256)

        self.setRotation(qrand() % (360 * 16))

        # In the C++ version of this example, this class is also derived from
        # QObject in order to receive timer events.  PyQt does not support
        # deriving from more than one wrapped class so we just create an
        # explicit timer instead.
        self.timer = QTimer()
        self.timer.timeout.connect(self.timerEvent)
        self.timer.start(1000 / 33)

    @staticmethod
    def normalizeAngle(angle):
        while angle < 0:
            angle += Mouse.TwoPi
        while angle > Mouse.TwoPi:
            angle -= Mouse.TwoPi
        return angle

    def boundingRect(self):
        return Mouse.BoundingRect

    # uncomment to override the shape used for collision detection
    # def shape(self):
    #     path = QPainterPath()
    #     path.addRect(-10, -20, 20, 40)
    #     return path;

    def paint(self, painter, option, widget):
        # Body.
        painter.setBrush(self.color)
        painter.drawRect(-20, -22, 40, 40)

        # Ears.
        if self in self.scene().collidingItems(self.driver):
            painter.setBrush(Qt.red)
        else:
            painter.setBrush(Qt.darkYellow)

        painter.drawEllipse(-17, -12, 16, 16)
        painter.drawEllipse(1, -12, 16, 16)


    def timerEvent(self):
        # Don't move too far away.
        lineToCenter = QLineF(QPointF(0, 0), self.mapFromScene(0, 0))
        if lineToCenter.length() > 150:
            angleToCenter = math.acos(lineToCenter.dx() / lineToCenter.length())
            if lineToCenter.dy() < 0:
                angleToCenter = Mouse.TwoPi - angleToCenter;
            angleToCenter = Mouse.normalizeAngle((Mouse.Pi - angleToCenter) + Mouse.Pi / 2)

            if angleToCenter < Mouse.Pi and angleToCenter > Mouse.Pi / 4:
                # Rotate left.
                self.angle += [-0.25, 0.25][self.angle < -Mouse.Pi / 2]
            elif angleToCenter >= Mouse.Pi and angleToCenter < (Mouse.Pi + Mouse.Pi / 2 + Mouse.Pi / 4):
                # Rotate right.
                self.angle += [-0.25, 0.25][self.angle < Mouse.Pi / 2]
        elif math.sin(self.angle) < 0:
            self.angle += 0.25
        elif math.sin(self.angle) > 0:
            self.angle -= 0.25

        # Try not to crash with any other mice.
        dangerMice = self.scene().items(QPolygonF([self.mapToScene(0, 0),
                                                         self.mapToScene(-30, -50),
                                                         self.mapToScene(30, -50)]))

        for item in dangerMice:
            if item is self:
                continue

            lineToMouse = QLineF(QPointF(0, 0), self.mapFromItem(item, 0, 0))
            angleToMouse = math.acos(lineToMouse.dx() / lineToMouse.length())
            if lineToMouse.dy() < 0:
                angleToMouse = Mouse.TwoPi - angleToMouse
            angleToMouse = Mouse.normalizeAngle((Mouse.Pi - angleToMouse) + Mouse.Pi / 2)

            if angleToMouse >= 0 and angleToMouse < Mouse.Pi / 2:
                # Rotate right.
                self.angle += 0.5
            elif angleToMouse <= Mouse.TwoPi and angleToMouse > (Mouse.TwoPi - Mouse.Pi / 2):
                # Rotate left.
                self.angle -= 0.5

        # Add some random movement.
        if len(dangerMice) > 1 and (qrand() % 10) == 0:
            if qrand() % 1:
                self.angle += (qrand() % 100) / 500.0
            else:
                self.angle -= (qrand() % 100) / 500.0

        self.speed += (-10 + qrand() % 100) / 100.0

        dx = math.sin(self.angle) * 10
        self.mouseEyeDirection = 0.0 if qAbs(dx / 5) < 1 else dx / 5

        self.setRotation(self.rotation() + dx)
        self.setPos(self.mapToParent(0, -(3 + math.sin(self.speed) * 3)))

class Driver(QGraphicsItem):
    # Create the bounding rectangle once.
    adjust = 1
    BoundingRect = QRectF(-10 - adjust, -14 - adjust, 20 + adjust, 26 + adjust)
    # Polygon
    polygonPoints = [
        QPointF(0.0, -13.0), # top
        QPointF(-10.0, 13.0), # bottom left
        QPointF(0.0, 5.0), # middle
        QPointF(10.0, 13.0), # bottom right
    ]
    polygon = QPolygonF(polygonPoints)

    def __init__(self):
        super(Driver, self).__init__()

    def boundingRect(self):
        return Driver.BoundingRect

    def shape(self):
        path = QPainterPath()
        path.addRect(-20, -20, 20, 40)
        return path;

    def paint(self, painter, option, widget):
        painter.setPen(Qt.black)
        painter.setBrush(Qt.red)
        painter.drawPolygon(Driver.polygon)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initWindow()

    def initWindow(self):
        grid = QGridLayout()
        self.setLayout(grid)

        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-500, -500, 1000, 1000)
        self.scene.setItemIndexMethod(QGraphicsScene.NoIndex)
        # a grid foreground
        self.scene.setBackgroundBrush(QBrush(Qt.lightGray, Qt.CrossPattern));

        # add driver to scene
        self.driver = Driver()
        self.driver.setPos(0, 80)
        self.scene.addItem(self.driver)

        # add center axes to scene
        self.scene.addLine(-220, 0, 220, 0) # x-axis
        self.scene.addLine(0, -140, 0, 140) # y-axis

        MouseCount = 0

        for i in range(MouseCount):
            mouse = Mouse(self.driver)
            mouse.setPos(math.sin((i * 6.28) / MouseCount) * 100,
                         math.cos((i * 6.28) / MouseCount) * 100)
            self.scene.addItem(mouse)


        self.gview = QGraphicsView(self.scene)
        self.gview.setRenderHint(QPainter.Antialiasing)
        # self.gview.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.gview.setDragMode(QGraphicsView.ScrollHandDrag)
        self.gview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);
        self.gview.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);
        # self.gview.resize(480, 320)
        self.gviewRotation = 0
        self.gview.rotate(self.gviewRotation)
        grid.addWidget(self.gview, 0, 0)
        # self.gview.show()

        self.gpsPoints = []
        for i in range(-20, 20, 5):
            for j in range(-20, 20, 5):
                self.gpsPoints.append((i, j))
        self.curPoint = 0

    def addPoint(self):
        point = self.gpsPoints[self.curPoint]
        self.curPoint += 1
        if (self.curPoint >= len(self.gpsPoints)):
            self.curPoint = 0
        circle = QGraphicsEllipseItem(point[0], point[1], 10, 10)
        self.scene.addItem(circle)

        self.driver.setPos(point[0], point[1])
        self.driver.setRotation(self.driver.rotation() - 10)

        viewCenterPoint = MainWindow.point_on_circle_at_angle(point, 80, self.driver.rotation() - 90)
        self.gview.centerOn(viewCenterPoint[0], viewCenterPoint[1])

        angleToRotate = self.gviewRotation - self.driver.rotation()

        self.gviewRotation = self.driver.rotation()
        self.gview.rotate(angleToRotate)

    @staticmethod
    def point_on_circle_at_angle(origin, radius, angle):
        angle = math.radians(angle)
        x = origin[0] + radius * math.cos(angle)
        y = origin[1] + radius * math.sin(angle)
        return (x, y)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A:
            self.addPoint()
        if event.key() == Qt.Key_Escape:
            sys.exit(0)
        if event.key() == Qt.Key_L:
            self.gviewRotation = (self.gviewRotation + 10) % 360
            self.gview.rotate(10)
            print('View Rotation: ' + str(self.gviewRotation))
        if event.key() == Qt.Key_R:
            self.gviewRotation = (self.gviewRotation - 10) % 360
            self.gview.rotate(-10)
            print('View Rotation: ' + str(self.gviewRotation))
        if event.key() == Qt.Key_C:
            self.gview.centerOn(self.driver)

if __name__ == '__main__':


    app = QApplication(sys.argv)

    view = MainWindow()
    view.setGeometry(0, 0, 330, 220)
    view.show()
    # view.showFullScreen()

    sys.exit(app.exec_())
