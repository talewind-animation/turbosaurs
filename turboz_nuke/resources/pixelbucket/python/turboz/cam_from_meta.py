import math
import nuke

def cam_from_metadata(node, cam, anim=True):
    '''
    Create a camera node based on VRay metadata.
    This works specifically on VRay data coming from maya.
    '''

    mDat = node.metadata()
    reqFields = ['exr/camera%s' % i for i in ('FocalLength', 'Aperture', 'Transform')]
    if not set( reqFields ).issubset( mDat ):
        nuke.critical( 'No metadata for camera found! Please select a read node with EXR metadata from VRay!' )
        return

    first = node.firstFrame()
    last = node.lastFrame()
    if not anim:
        last = first

    frame_range = nuke.FrameRange('{}-{}'.format(first, last))

    cam['useMatrix'].setValue( False )

    for k in ( 'focal', 'haperture', 'vaperture', 'translate', 'rotate'):
        cam[k].setAnimated()

    task = nuke.ProgressTask( 'Baking camera from meta data in %s' % node.name() )

    for curTask, frame in enumerate( frame_range ):
        if task.isCancelled():
            break
        task.setMessage( 'processing frame %s' % frame )

        hap = node.metadata( 'exr/cameraAperture', frame ) # get horizontal aperture
        fov = node.metadata( 'exr/cameraFov', frame ) # get camera FOV

        focal = float(hap) / ( 2.0 * math.tan( math.radians(fov) * 0.5 ) ) # convert the fov and aperture into focal length

        width = node.metadata( 'input/width', frame )
        height = node.metadata( 'input/height', frame )
        aspect = float(width) / float(height) # calulate aspect ratio from width and height
        vap = float(hap) / aspect # calculate vertical aperture from aspect ratio

        cam['focal'].setValueAt( float(focal), frame )
        cam['haperture'].setValueAt( float(hap), frame )
        cam['vaperture'].setValueAt( float(vap), frame )

        matrixCamera = node.metadata( 'exr/cameraTransform', frame ) # get camera transform data

        # create a matrix to shove the original data into
        matrixCreated = nuke.math.Matrix4()

        for k,v in enumerate( matrixCamera ):
            matrixCreated[k] = v

        matrixCreated.rotateX( math.radians(-90) ) # this is needed for VRay, it's a counter clockwise rotation
        translate = matrixCreated.transform( nuke.math.Vector3(0,0,0) )  # get a vector that represents the camera translation
        rotate = matrixCreated.rotationsZXY() # give us xyz rotations from cam matrix (must be converted to degrees)

        cam['translate'].setValueAt( float(translate.x), frame, 0 )
        cam['translate'].setValueAt( float(translate.y), frame, 1 )
        cam['translate'].setValueAt( float(translate.z), frame, 2 )
        cam['rotate'].setValueAt( float( math.degrees( rotate[0] ) ), frame, 0 )
        cam['rotate'].setValueAt( float( math.degrees( rotate[1] ) ), frame, 1 )
        cam['rotate'].setValueAt( float( math.degrees( rotate[2] ) ), frame, 2 )

        task.setProgress( int( float(curTask) / frame_range.frames() * 100 ) )

def bake(anim=True, node=None):
    if not node:
        node = nuke.selectedNode()
    cam = nuke.toNode('__shotcam__')
    if node.Class() == 'Read':
        nuke.root()['first_frame'].setValue(node['first'].getValue())
        nuke.root()['last_frame'].setValue(node['last'].getValue())
        nuke.frame(node['first'].getValue())
    cam_from_metadata(node, cam, anim=anim)

def bake_cam():
    ch = nuke.toNode("CH_IN_beauty")
    bg = nuke.toNode("BG_IN_beauty")
    if bg:
        if bg['first'].getValue() == bg['last'].getValue():
            bake(anim=False, node=ch)
        else:
            bake(node=ch)
    else:
        bake(node=ch)