from __future__ import print_function
import numpy as np
import numpy.testing as npt
import unittest

# Tensorflow is used to verify the results of numpy computations - you can
# remove its usage if you don't need the testing.
import tensorflow as tf


def conv2d_single_channel(input, w):
    """Two-dimensional convolution of a single channel.

    Uses SAME padding with 0s, a stride of 1 and no dilation.

    input: input array with shape (height, width)
    w: filter array with shape (fd, fd) with odd fd.

    Returns a result with the same shape as input.
    """
    assert w.shape[0] == w.shape[1] and w.shape[0] % 2 == 1

    # SAME padding with zeros: creating a new padded array to simplify index
    # calculations and to avoid checking boundary conditions in the inner loop.
    # padded_input is like input, but padded on all sides with
    # half-the-filter-width of zeros.
    padded_input = np.pad(input,
                          pad_width=w.shape[0] // 2,
                          mode='constant',
                          constant_values=0)

    output = np.zeros_like(input)
    for i in range(output.shape[0]):
        for j in range(output.shape[1]):
            # This inner double loop computes every output element, by
            # multiplying the corresponding window into the input with the
            # filter.
            for fi in range(w.shape[0]):
                for fj in range(w.shape[1]):
                    output[i, j] += padded_input[i + fi, j + fj] * w[fi, fj]
    return output


def conv2d_multi_channel(input, w):
    """Two-dimensional convolution with multiple channels.

    Uses SAME padding with 0s, a stride of 1 and no dilation.

    input: input array with shape (height, width, in_depth)
    w: filter array with shape (fd, fd, in_depth, out_depth) with odd fd.
       in_depth is the number of input channels, and has the be the same as
       input's in_depth; out_depth is the number of output channels.

    Returns a result with shape (height, width, out_depth).
    """
    assert w.shape[0] == w.shape[1] and w.shape[0] % 2 == 1

    padw = w.shape[0] // 2
    padded_input = np.pad(input,
                          pad_width=((padw, padw), (padw, padw), (0, 0)),
                          mode='constant',
                          constant_values=0)

    height, width, in_depth = input.shape
    assert in_depth == w.shape[2]
    out_depth = w.shape[3]
    output = np.zeros((height, width, out_depth))

    for out_c in range(out_depth):
        # For each output channel, perform 2d convolution summed across all
        # input channels.
        for i in range(height):
            for j in range(width):
                # Now the inner loop also works across all input channels.
                for c in range(in_depth):
                    for fi in range(w.shape[0]):
                        for fj in range(w.shape[1]):
                            w_element = w[fi, fj, c, out_c]
                            output[i, j, out_c] += (
                                padded_input[i + fi, j + fj, c] * w_element)

    return output



def tf_conv2d_single_channel(input, w):
    """Single-channel conv2d using TF.

    Params same as in conv2d_single_channel.
    """
    # We only have one item in our "batch", one input channel and one output
    # channel; prepare the shapes TF expects for the conv2d op.
    input_4d = tf.reshape(tf.constant(input, dtype=tf.float32),
                         [1, input.shape[0], input.shape[1], 1])
    kernel_4d = tf.reshape(tf.constant(w, dtype=tf.float32),
                           [w.shape[0], w.shape[1], 1, 1])
    output = tf.nn.conv2d(input_4d, kernel_4d,
                          strides=[1, 1, 1, 1], padding='SAME')
    with tf.Session() as sess:
        ans = sess.run(output)
        # Remove the degenerate batch dimension, since we use batch 1.
        return ans.reshape(input.shape)


def tf_conv2d_multi_channel(input, w):
    """Multi-channel conv2d using TF.

    Params same as in conv2d_multi_channel.
    """
    # Here the input we get already has the out_depth dimension; we just have to
    # set batch to 1.
    input_4d = tf.reshape(tf.constant(input, dtype=tf.float32),
                          [1, input.shape[0], input.shape[1], input.shape[2]])
    kernel_4d = tf.constant(w, dtype=tf.float32)
    output = tf.nn.conv2d(input_4d, kernel_4d,
                          strides=[1, 1, 1, 1], padding='SAME')
    with tf.Session() as sess:
        ans = sess.run(output)
        # Remove the degenerate batch dimension, since we use batch 1.
        return ans.reshape((input.shape[0], input.shape[1], w.shape[3]))


class TestConvs(unittest.TestCase):
    def test_single_channel(self):
        inp = np.linspace(-5, 5, 36).reshape(6, 6)

        w = np.linspace(0, 8, 9)[::-1].reshape(3, 3)
        np_ans = conv2d_single_channel(inp, w)
        tf_ans = tf_conv2d_single_channel(inp, w)
        npt.assert_almost_equal(np_ans, tf_ans, decimal=3)

        w = np.array([[1, -1, 1], [0, -1, 1], [1, -1, 0]])
        np_ans = conv2d_single_channel(inp, w)
        tf_ans = tf_conv2d_single_channel(inp, w)
        npt.assert_almost_equal(np_ans, tf_ans, decimal=4)

    def test_multi_channel(self):
        # input is 6x6, with 3 channels
        # filter is 3x3 with 3 input channels, 4 output channels
        inp = np.linspace(-5, 5, 6*6*3).reshape(6, 6, 3)

        w = np.linspace(0, 107, 108).reshape(3, 3, 3, 4)
        np_ans = conv2d_multi_channel(inp, w)
        tf_ans = tf_conv2d_multi_channel(inp, w)
        npt.assert_almost_equal(np_ans, tf_ans, decimal=3)

        w = np.ones((3, 3, 3, 4))
        w[0, 0, 0, 0] = -1
        w[0, 0, 0, 1] = -1
        w[0, 0, 0, 2] = -1
        w[0, 0, 0, 3] = -1
        np_ans = conv2d_multi_channel(inp, w)
        tf_ans = tf_conv2d_multi_channel(inp, w)
        npt.assert_almost_equal(np_ans, tf_ans, decimal=3)


if __name__ == '__main__':
    unittest.main()

    inp = np.ones((6, 6))
    w = np.zeros((3, 3))
    w[0, 0] = 1
    w[1, 1] = 1
    w[2, 2] = 1

    out = conv2d_single_channel(inp, w)
    #print(out)

    inp = np.ones((6, 6, 3))
    w = np.zeros((3, 3, 3, 5))
    w[0, 0, 0, 1] = 1
    w[0, 1, 0, 1] = 1
    w[1, 1, 0, 1] = 1
    w[1, 1, 1, 1] = 1
    w[1, 1, 2, 1] = 1
    w[1, 1, 2, 1] = 1
    w[1, 1, 2, 0] = 1

    out = conv2d_multi_channel(inp, w)
    print(out)

    outtf = tf_conv2d_multi_channel(inp, w)
    print(outtf)
